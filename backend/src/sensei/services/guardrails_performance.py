"""
Guardrails & Performance Infrastructure.

On-device resource management, PII redaction, and HITL consistency monitoring
for AI operations.

Features:
- CPU/RAM monitoring with AI task throttling
- Dynamic model loading/unloading
- Emergency kill-switch for high load
- Local NER-based PII redaction
- Redaction audit logging
- PII re-hydration for authorized users
- AI drift analytics
- Prompt A/B testing
- Consistency scoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
import hashlib
import re
import secrets
import threading
import time
import uuid


# =============================================================================
# Enums
# =============================================================================

class ResourceType(Enum):
    """System resource types."""
    
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    GPU = "gpu"


class TaskPriority(Enum):
    """AI task priority levels."""
    
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    """AI task status."""
    
    PENDING = "pending"
    RUNNING = "running"
    THROTTLED = "throttled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PIIType(Enum):
    """Types of PII."""
    
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


class RedactionMethod(Enum):
    """How PII was redacted."""
    
    MASKED = "masked"
    REPLACED = "replaced"
    REMOVED = "removed"
    HASHED = "hashed"


class DriftSeverity(Enum):
    """Severity of AI drift."""
    
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Constants
# =============================================================================

KILL_SWITCH_THRESHOLD = 95.0  # System load percentage
THROTTLE_THRESHOLD = 80.0
NORMAL_THRESHOLD = 60.0

# PII Patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-.\s]?){3}\d{4}\b')

# Common name prefixes/suffixes for name detection
NAME_PREFIXES = ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.']
NAME_CONTEXTS = ['Dear', 'Hi', 'Hello', 'Regards', 'Sincerely', 'From:', 'To:', 'Attn:']


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ResourceMetrics:
    """System resource metrics."""
    
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    disk_percent: float = 0.0
    disk_available_gb: float = 0.0
    gpu_percent: float | None = None
    gpu_memory_mb: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AITask:
    """AI inference task."""
    
    task_id: str
    name: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    model_name: str = ""
    estimated_memory_mb: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float | None:
        """Get task duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class LoadedModel:
    """Loaded AI model."""
    
    model_id: str
    name: str
    memory_mb: float
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0
    is_lightweight: bool = False


@dataclass
class PIIMatch:
    """A detected PII match."""
    
    pii_type: PIIType
    start: int
    end: int
    original_length: int
    redaction_token: str
    method: RedactionMethod = RedactionMethod.MASKED


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    
    result_id: str
    redacted_text: str
    matches: list[PIIMatch] = field(default_factory=list)
    pii_counts: dict[str, int] = field(default_factory=dict)
    redacted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RedactionAuditEntry:
    """Audit log entry for redaction."""
    
    entry_id: str
    result_id: str
    pii_type: PIIType
    method: RedactionMethod
    original_length: int
    context_hash: str  # Hash of surrounding context (without PII)
    redacted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PIIToken:
    """Token for re-hydrating PII."""
    
    token: str
    pii_type: PIIType
    encrypted_value: bytes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


@dataclass
class SuggestionFeedback:
    """Feedback on an AI suggestion."""
    
    feedback_id: str
    suggestion_id: str
    model_name: str
    prompt_variant: str = "default"
    accepted: bool = False
    corrected: bool = False
    correction_magnitude: float = 0.0  # 0-1 scale of how different
    feedback_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DriftMetrics:
    """AI drift metrics."""
    
    model_name: str
    period_start: datetime
    period_end: datetime
    total_suggestions: int = 0
    accepted_count: int = 0
    corrected_count: int = 0
    correction_rate: float = 0.0
    avg_correction_magnitude: float = 0.0
    severity: DriftSeverity = DriftSeverity.NONE


@dataclass
class PromptVariant:
    """A prompt variant for A/B testing."""
    
    variant_id: str
    name: str
    prompt_template: str
    weight: float = 1.0
    total_uses: int = 0
    acceptance_rate: float = 0.0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConsistencyScore:
    """Overall AI consistency score."""
    
    model_name: str
    score: float  # 0-100
    accepted: int
    corrected: int
    total: int
    trend: str = "stable"  # improving, stable, declining
    period_days: int = 7
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Resource Monitor
# =============================================================================

class ResourceMonitor:
    """
    Monitor system resources and manage AI task throttling.
    """
    
    def __init__(
        self,
        kill_threshold: float = KILL_SWITCH_THRESHOLD,
        throttle_threshold: float = THROTTLE_THRESHOLD,
    ):
        """Initialize resource monitor."""
        self._kill_threshold = kill_threshold
        self._throttle_threshold = throttle_threshold
        self._current_metrics = ResourceMetrics()
        self._kill_switch_active = False
        self._running_tasks: dict[str, AITask] = {}
        self._loaded_models: dict[str, LoadedModel] = {}
        self._lock = threading.Lock()
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics (simulated)."""
        # In production, would use psutil or similar
        # Simulating metrics for testing
        import random
        
        self._current_metrics = ResourceMetrics(
            cpu_percent=random.uniform(20, 60),
            memory_percent=random.uniform(30, 70),
            memory_available_mb=random.uniform(4000, 16000),
            disk_percent=random.uniform(40, 80),
            disk_available_gb=random.uniform(50, 500),
        )
        
        return self._current_metrics
    
    def set_metrics(self, metrics: ResourceMetrics):
        """Set metrics (for testing)."""
        self._current_metrics = metrics
    
    def is_overloaded(self) -> bool:
        """Check if system is overloaded."""
        return (
            self._current_metrics.cpu_percent >= self._kill_threshold or
            self._current_metrics.memory_percent >= self._kill_threshold
        )
    
    def should_throttle(self) -> bool:
        """Check if tasks should be throttled."""
        return (
            self._current_metrics.cpu_percent >= self._throttle_threshold or
            self._current_metrics.memory_percent >= self._throttle_threshold
        )
    
    def activate_kill_switch(self) -> list[str]:
        """Activate emergency kill switch for all AI tasks."""
        with self._lock:
            self._kill_switch_active = True
            cancelled_tasks = []
            
            for task_id, task in self._running_tasks.items():
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now(timezone.utc)
                    task.error = "Emergency kill switch activated"
                    cancelled_tasks.append(task_id)
            
            return cancelled_tasks
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch."""
        with self._lock:
            self._kill_switch_active = False
    
    def is_kill_switch_active(self) -> bool:
        """Check if kill switch is active."""
        return self._kill_switch_active
    
    def can_start_task(self, task: AITask) -> tuple[bool, str]:
        """Check if a task can be started."""
        if self._kill_switch_active:
            return False, "Kill switch is active"
        
        if self.is_overloaded():
            return False, "System is overloaded"
        
        if self.should_throttle():
            if task.priority.value >= TaskPriority.NORMAL.value:
                return False, "System is throttled, only high-priority tasks allowed"
        
        # Check memory
        available_mb = self._current_metrics.memory_available_mb
        if task.estimated_memory_mb > available_mb * 0.5:
            return False, f"Insufficient memory: need {task.estimated_memory_mb}MB, have {available_mb}MB"
        
        return True, "OK"
    
    def register_task(self, task: AITask) -> bool:
        """Register a task as running."""
        can_start, reason = self.can_start_task(task)
        if not can_start:
            task.status = TaskStatus.THROTTLED
            task.error = reason
            return False
        
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            self._running_tasks[task.task_id] = task
        
        return True
    
    def complete_task(self, task_id: str, success: bool = True, error: str | None = None):
        """Mark a task as complete."""
        with self._lock:
            if task_id in self._running_tasks:
                task = self._running_tasks[task_id]
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)
                task.error = error
    
    def get_running_tasks(self) -> list[AITask]:
        """Get all running tasks."""
        return [
            t for t in self._running_tasks.values()
            if t.status == TaskStatus.RUNNING
        ]


# =============================================================================
# Model Manager
# =============================================================================

class ModelManager:
    """
    Manage dynamic model loading/unloading.
    """
    
    def __init__(
        self,
        max_memory_mb: float = 8000,
        idle_timeout_minutes: int = 30,
    ):
        """Initialize model manager."""
        self._max_memory_mb = max_memory_mb
        self._idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self._models: dict[str, LoadedModel] = {}
        self._lightweight_fallbacks: dict[str, str] = {}  # model -> fallback
    
    @property
    def total_memory_used(self) -> float:
        """Get total memory used by loaded models."""
        return sum(m.memory_mb for m in self._models.values())
    
    @property
    def available_memory(self) -> float:
        """Get available memory for models."""
        return self._max_memory_mb - self.total_memory_used
    
    def load_model(self, model: LoadedModel) -> bool:
        """Load a model into memory."""
        if model.model_id in self._models:
            return True  # Already loaded
        
        if model.memory_mb > self.available_memory:
            # Try to unload idle models
            self._unload_idle_models()
            
            if model.memory_mb > self.available_memory:
                return False
        
        self._models[model.model_id] = model
        return True
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory."""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False
    
    def get_model(self, model_id: str) -> LoadedModel | None:
        """Get a loaded model."""
        model = self._models.get(model_id)
        if model:
            model.last_used = datetime.now(timezone.utc)
            model.use_count += 1
        return model
    
    def _unload_idle_models(self):
        """Unload models that haven't been used recently."""
        now = datetime.now(timezone.utc)
        to_unload = []
        
        for model_id, model in self._models.items():
            if now - model.last_used > self._idle_timeout:
                to_unload.append(model_id)
        
        for model_id in to_unload:
            self.unload_model(model_id)
    
    def register_fallback(self, model_id: str, fallback_id: str):
        """Register a lightweight fallback for a model."""
        self._lightweight_fallbacks[model_id] = fallback_id
    
    def get_fallback(self, model_id: str) -> str | None:
        """Get fallback model for given model."""
        return self._lightweight_fallbacks.get(model_id)
    
    def switch_to_fallback(self, model_id: str) -> bool:
        """Switch to fallback model."""
        fallback_id = self.get_fallback(model_id)
        if not fallback_id:
            return False
        
        # Unload original
        self.unload_model(model_id)
        
        # Load fallback (if not already loaded)
        if fallback_id not in self._models:
            fallback = LoadedModel(
                model_id=fallback_id,
                name=f"{model_id}_lite",
                memory_mb=100,  # Lightweight
                is_lightweight=True,
            )
            return self.load_model(fallback)
        
        return True
    
    def get_loaded_models(self) -> list[LoadedModel]:
        """Get all loaded models."""
        return list(self._models.values())


# =============================================================================
# PII Redactor
# =============================================================================

class PIIRedactor:
    """
    Local NER-based PII redaction.
    """
    
    def __init__(
        self,
        mask_char: str = "*",
        hash_salt: str | None = None,
    ):
        """Initialize PII redactor."""
        self._mask_char = mask_char
        self._hash_salt = hash_salt or secrets.token_hex(16)
        self._tokens: dict[str, PIIToken] = {}
        self._audit_log: list[RedactionAuditEntry] = []
    
    def _detect_emails(self, text: str) -> list[PIIMatch]:
        """Detect email addresses."""
        matches = []
        for match in EMAIL_PATTERN.finditer(text):
            token = self._generate_token()
            matches.append(PIIMatch(
                pii_type=PIIType.EMAIL,
                start=match.start(),
                end=match.end(),
                original_length=len(match.group()),
                redaction_token=token,
            ))
        return matches
    
    def _detect_phones(self, text: str) -> list[PIIMatch]:
        """Detect phone numbers."""
        matches = []
        for match in PHONE_PATTERN.finditer(text):
            token = self._generate_token()
            matches.append(PIIMatch(
                pii_type=PIIType.PHONE,
                start=match.start(),
                end=match.end(),
                original_length=len(match.group()),
                redaction_token=token,
            ))
        return matches
    
    def _detect_ssn(self, text: str) -> list[PIIMatch]:
        """Detect SSNs."""
        matches = []
        for match in SSN_PATTERN.finditer(text):
            token = self._generate_token()
            matches.append(PIIMatch(
                pii_type=PIIType.SSN,
                start=match.start(),
                end=match.end(),
                original_length=len(match.group()),
                redaction_token=token,
            ))
        return matches
    
    def _detect_credit_cards(self, text: str) -> list[PIIMatch]:
        """Detect credit card numbers."""
        matches = []
        for match in CREDIT_CARD_PATTERN.finditer(text):
            token = self._generate_token()
            matches.append(PIIMatch(
                pii_type=PIIType.CREDIT_CARD,
                start=match.start(),
                end=match.end(),
                original_length=len(match.group()),
                redaction_token=token,
            ))
        return matches
    
    def _detect_names(self, text: str) -> list[PIIMatch]:
        """Detect names using context clues."""
        matches = []
        
        # Look for names after common prefixes
        for prefix in NAME_PREFIXES:
            pattern = re.compile(rf'{re.escape(prefix)}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)')
            for match in pattern.finditer(text):
                token = self._generate_token()
                # Match just the name part, not the prefix
                name_start = match.start() + len(prefix) + 1
                matches.append(PIIMatch(
                    pii_type=PIIType.NAME,
                    start=name_start,
                    end=match.end(),
                    original_length=match.end() - name_start,
                    redaction_token=token,
                ))
        
        # Look for names in context
        for context in NAME_CONTEXTS:
            pattern = re.compile(rf'{context}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)')
            for match in pattern.finditer(text):
                token = self._generate_token()
                name_start = match.start() + len(context) + 1
                matches.append(PIIMatch(
                    pii_type=PIIType.NAME,
                    start=name_start,
                    end=match.end(),
                    original_length=match.end() - name_start,
                    redaction_token=token,
                ))
        
        return matches
    
    def _generate_token(self) -> str:
        """Generate a unique redaction token."""
        return f"[REDACTED_{secrets.token_hex(4).upper()}]"
    
    def _get_context_hash(self, text: str, start: int, end: int) -> str:
        """Get hash of surrounding context."""
        context_start = max(0, start - 20)
        context_end = min(len(text), end + 20)
        context = text[context_start:start] + text[end:context_end]
        return hashlib.sha256((context + self._hash_salt).encode()).hexdigest()[:16]
    
    def redact(
        self,
        text: str,
        pii_types: list[PIIType] | None = None,
        method: RedactionMethod = RedactionMethod.MASKED,
    ) -> RedactionResult:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            pii_types: Types of PII to redact (all if None)
            method: Redaction method
        
        Returns:
            RedactionResult with redacted text and audit info
        """
        if pii_types is None:
            pii_types = list(PIIType)
        
        all_matches = []
        
        # Detect each type
        if PIIType.EMAIL in pii_types:
            all_matches.extend(self._detect_emails(text))
        if PIIType.PHONE in pii_types:
            all_matches.extend(self._detect_phones(text))
        if PIIType.SSN in pii_types:
            all_matches.extend(self._detect_ssn(text))
        if PIIType.CREDIT_CARD in pii_types:
            all_matches.extend(self._detect_credit_cards(text))
        if PIIType.NAME in pii_types:
            all_matches.extend(self._detect_names(text))
        
        # Sort by position (reverse for replacement)
        all_matches.sort(key=lambda m: m.start, reverse=True)
        
        # Apply redactions
        result_text = text
        pii_counts: dict[str, int] = {}
        result_id = str(uuid.uuid4())
        
        for match in all_matches:
            match.method = method
            original = result_text[match.start:match.end]
            
            if method == RedactionMethod.MASKED:
                replacement = self._mask_char * match.original_length
            elif method == RedactionMethod.REPLACED:
                replacement = match.redaction_token
            elif method == RedactionMethod.REMOVED:
                replacement = ""
            elif method == RedactionMethod.HASHED:
                replacement = hashlib.sha256(
                    (original + self._hash_salt).encode()
                ).hexdigest()[:16]
            else:
                replacement = self._mask_char * match.original_length
            
            result_text = result_text[:match.start] + replacement + result_text[match.end:]
            
            # Store token for re-hydration
            self._tokens[match.redaction_token] = PIIToken(
                token=match.redaction_token,
                pii_type=match.pii_type,
                encrypted_value=original.encode(),  # Would encrypt in production
            )
            
            # Update counts
            pii_type_name = match.pii_type.value
            pii_counts[pii_type_name] = pii_counts.get(pii_type_name, 0) + 1
            
            # Audit log
            self._audit_log.append(RedactionAuditEntry(
                entry_id=str(uuid.uuid4()),
                result_id=result_id,
                pii_type=match.pii_type,
                method=method,
                original_length=match.original_length,
                context_hash=self._get_context_hash(text, match.start, match.end),
            ))
        
        # Re-sort matches for result
        all_matches.sort(key=lambda m: m.start)
        
        return RedactionResult(
            result_id=result_id,
            redacted_text=result_text,
            matches=all_matches,
            pii_counts=pii_counts,
        )
    
    def rehydrate(
        self,
        redacted_text: str,
        authorized: bool = False,
    ) -> str:
        """Re-hydrate PII for authorized users."""
        if not authorized:
            return redacted_text
        
        result = redacted_text
        for token, pii_token in self._tokens.items():
            if token in result:
                original = pii_token.encrypted_value.decode()
                result = result.replace(token, original)
        
        return result
    
    def get_audit_log(
        self,
        result_id: str | None = None,
    ) -> list[RedactionAuditEntry]:
        """Get redaction audit log."""
        if result_id:
            return [e for e in self._audit_log if e.result_id == result_id]
        return self._audit_log.copy()


# =============================================================================
# HITL Consistency Monitor
# =============================================================================

class HITLConsistencyMonitor:
    """
    Monitor Human-in-the-Loop consistency and AI drift.
    """
    
    def __init__(
        self,
        drift_window_days: int = 7,
        drift_threshold: float = 0.3,  # 30% correction rate is concerning
    ):
        """Initialize monitor."""
        self._drift_window_days = drift_window_days
        self._drift_threshold = drift_threshold
        self._feedback: list[SuggestionFeedback] = []
        self._prompt_variants: dict[str, PromptVariant] = {}
    
    def record_feedback(self, feedback: SuggestionFeedback):
        """Record feedback on an AI suggestion."""
        self._feedback.append(feedback)
    
    def calculate_drift(self, model_name: str) -> DriftMetrics:
        """Calculate drift metrics for a model."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=self._drift_window_days)
        
        relevant = [
            f for f in self._feedback
            if f.model_name == model_name and f.feedback_at >= window_start
        ]
        
        total = len(relevant)
        if total == 0:
            return DriftMetrics(
                model_name=model_name,
                period_start=window_start,
                period_end=now,
            )
        
        accepted = sum(1 for f in relevant if f.accepted)
        corrected = sum(1 for f in relevant if f.corrected)
        correction_rate = corrected / total if total > 0 else 0
        
        avg_magnitude = (
            sum(f.correction_magnitude for f in relevant if f.corrected) / corrected
            if corrected > 0 else 0
        )
        
        # Determine severity
        if correction_rate < 0.1:
            severity = DriftSeverity.NONE
        elif correction_rate < 0.2:
            severity = DriftSeverity.LOW
        elif correction_rate < 0.3:
            severity = DriftSeverity.MEDIUM
        elif correction_rate < 0.5:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL
        
        return DriftMetrics(
            model_name=model_name,
            period_start=window_start,
            period_end=now,
            total_suggestions=total,
            accepted_count=accepted,
            corrected_count=corrected,
            correction_rate=correction_rate,
            avg_correction_magnitude=avg_magnitude,
            severity=severity,
        )
    
    def register_prompt_variant(self, variant: PromptVariant):
        """Register a prompt variant for A/B testing."""
        self._prompt_variants[variant.variant_id] = variant
    
    def select_prompt_variant(self, variants: list[str] | None = None) -> PromptVariant | None:
        """Select a prompt variant based on weights."""
        if variants:
            available = [
                v for v in self._prompt_variants.values()
                if v.variant_id in variants and v.is_active
            ]
        else:
            available = [v for v in self._prompt_variants.values() if v.is_active]
        
        if not available:
            return None
        
        # Weighted random selection
        total_weight = sum(v.weight for v in available)
        if total_weight == 0:
            return available[0]
        
        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for variant in available:
            cumulative += variant.weight
            if r <= cumulative:
                variant.total_uses += 1
                return variant
        
        return available[-1]
    
    def update_variant_performance(self, variant_id: str, accepted: bool):
        """Update variant performance based on feedback."""
        if variant_id not in self._prompt_variants:
            return
        
        variant = self._prompt_variants[variant_id]
        
        # Update acceptance rate with exponential moving average
        alpha = 0.1
        new_value = 1.0 if accepted else 0.0
        variant.acceptance_rate = (
            alpha * new_value + (1 - alpha) * variant.acceptance_rate
        )
        
        # Adjust weight based on performance
        if variant.acceptance_rate > 0.8:
            variant.weight = min(variant.weight * 1.1, 10.0)
        elif variant.acceptance_rate < 0.5:
            variant.weight = max(variant.weight * 0.9, 0.1)
    
    def calculate_consistency_score(self, model_name: str) -> ConsistencyScore:
        """Calculate overall consistency score."""
        drift = self.calculate_drift(model_name)
        
        if drift.total_suggestions == 0:
            return ConsistencyScore(
                model_name=model_name,
                score=100.0,
                accepted=0,
                corrected=0,
                total=0,
            )
        
        # Score is based on acceptance rate and correction magnitude
        base_score = (drift.accepted_count / drift.total_suggestions) * 100
        
        # Penalize for high correction magnitudes
        magnitude_penalty = drift.avg_correction_magnitude * 20
        
        score = max(0, base_score - magnitude_penalty)
        
        # Determine trend by comparing to older data
        older_start = drift.period_start - timedelta(days=self._drift_window_days)
        older = [
            f for f in self._feedback
            if f.model_name == model_name 
            and older_start <= f.feedback_at < drift.period_start
        ]
        
        if len(older) > 10:
            older_acceptance = sum(1 for f in older if f.accepted) / len(older)
            current_acceptance = drift.accepted_count / drift.total_suggestions
            
            if current_acceptance > older_acceptance + 0.05:
                trend = "improving"
            elif current_acceptance < older_acceptance - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return ConsistencyScore(
            model_name=model_name,
            score=score,
            accepted=drift.accepted_count,
            corrected=drift.corrected_count,
            total=drift.total_suggestions,
            trend=trend,
            period_days=self._drift_window_days,
        )
    
    def get_variant_performance(self) -> list[dict[str, Any]]:
        """Get performance metrics for all variants."""
        return [
            {
                "variant_id": v.variant_id,
                "name": v.name,
                "total_uses": v.total_uses,
                "acceptance_rate": v.acceptance_rate,
                "weight": v.weight,
                "is_active": v.is_active,
            }
            for v in self._prompt_variants.values()
        ]


# =============================================================================
# Factory Functions
# =============================================================================

def create_resource_monitor(
    kill_threshold: float = KILL_SWITCH_THRESHOLD,
    throttle_threshold: float = THROTTLE_THRESHOLD,
) -> ResourceMonitor:
    """Create resource monitor."""
    return ResourceMonitor(
        kill_threshold=kill_threshold,
        throttle_threshold=throttle_threshold,
    )


def create_model_manager(
    max_memory_mb: float = 8000,
    idle_timeout_minutes: int = 30,
) -> ModelManager:
    """Create model manager."""
    return ModelManager(
        max_memory_mb=max_memory_mb,
        idle_timeout_minutes=idle_timeout_minutes,
    )


def create_pii_redactor(
    mask_char: str = "*",
) -> PIIRedactor:
    """Create PII redactor."""
    return PIIRedactor(mask_char=mask_char)


def create_hitl_monitor(
    drift_window_days: int = 7,
    drift_threshold: float = 0.3,
) -> HITLConsistencyMonitor:
    """Create HITL consistency monitor."""
    return HITLConsistencyMonitor(
        drift_window_days=drift_window_days,
        drift_threshold=drift_threshold,
    )

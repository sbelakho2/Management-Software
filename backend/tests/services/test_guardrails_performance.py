"""
Tests for Guardrails & Performance Infrastructure.

Tests cover:
- On-device resource management
- CPU/RAM monitoring and throttling
- Emergency kill-switch
- Dynamic model loading/unloading
- PII redaction (NER-based)
- Redaction audit logging
- PII re-hydration
- AI drift analytics
- Prompt A/B testing
- Consistency scoring
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.guardrails_performance import (
    # Enums
    ResourceType,
    TaskPriority,
    TaskStatus,
    PIIType,
    RedactionMethod,
    DriftSeverity,
    # Data models
    ResourceMetrics,
    AITask,
    LoadedModel,
    PIIMatch,
    RedactionResult,
    RedactionAuditEntry,
    PIIToken,
    SuggestionFeedback,
    DriftMetrics,
    PromptVariant,
    ConsistencyScore,
    # Components
    ResourceMonitor,
    ModelManager,
    PIIRedactor,
    HITLConsistencyMonitor,
    # Factory functions
    create_resource_monitor,
    create_model_manager,
    create_pii_redactor,
    create_hitl_monitor,
    # Constants
    KILL_SWITCH_THRESHOLD,
    THROTTLE_THRESHOLD,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def resource_monitor() -> ResourceMonitor:
    """Create resource monitor for testing."""
    return ResourceMonitor()


@pytest.fixture
def model_manager() -> ModelManager:
    """Create model manager for testing."""
    return ModelManager(max_memory_mb=4000, idle_timeout_minutes=5)


@pytest.fixture
def pii_redactor() -> PIIRedactor:
    """Create PII redactor for testing."""
    return PIIRedactor()


@pytest.fixture
def hitl_monitor() -> HITLConsistencyMonitor:
    """Create HITL monitor for testing."""
    return HITLConsistencyMonitor()


@pytest.fixture
def sample_task() -> AITask:
    """Sample AI task."""
    return AITask(
        task_id="task-001",
        name="Text Generation",
        priority=TaskPriority.NORMAL,
        model_name="gpt-neo",
        estimated_memory_mb=500,
    )


@pytest.fixture
def sample_model() -> LoadedModel:
    """Sample loaded model."""
    return LoadedModel(
        model_id="model-001",
        name="sentence-transformer",
        memory_mb=500,
    )


# =============================================================================
# Test Enums
# =============================================================================

class TestEnums:
    """Test enum values."""
    
    def test_resource_type_values(self):
        """Test resource type enum."""
        assert ResourceType.CPU.value == "cpu"
        assert ResourceType.MEMORY.value == "memory"
        assert ResourceType.GPU.value == "gpu"
    
    def test_task_priority_values(self):
        """Test task priority enum."""
        assert TaskPriority.CRITICAL.value == 0
        assert TaskPriority.HIGH.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.LOW.value == 3
        assert TaskPriority.BACKGROUND.value == 4
    
    def test_task_status_values(self):
        """Test task status enum."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.THROTTLED.value == "throttled"
    
    def test_pii_type_values(self):
        """Test PII type enum."""
        assert PIIType.EMAIL.value == "email"
        assert PIIType.PHONE.value == "phone"
        assert PIIType.SSN.value == "ssn"
    
    def test_redaction_method_values(self):
        """Test redaction method enum."""
        assert RedactionMethod.MASKED.value == "masked"
        assert RedactionMethod.HASHED.value == "hashed"
    
    def test_drift_severity_values(self):
        """Test drift severity enum."""
        assert DriftSeverity.NONE.value == "none"
        assert DriftSeverity.CRITICAL.value == "critical"


# =============================================================================
# Test Data Models
# =============================================================================

class TestResourceMetrics:
    """Test ResourceMetrics dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        metrics = ResourceMetrics()
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_percent == 0.0
        assert metrics.gpu_percent is None
    
    def test_with_values(self):
        """Test with custom values."""
        metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=8000,
        )
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_available_mb == 8000


class TestAITask:
    """Test AITask dataclass."""
    
    def test_defaults(self, sample_task):
        """Test default values."""
        assert sample_task.status == TaskStatus.PENDING
        assert sample_task.started_at is None
    
    def test_duration_none_when_not_complete(self, sample_task):
        """Test duration is None when not complete."""
        assert sample_task.duration_ms is None
    
    def test_duration_calculated(self, sample_task):
        """Test duration calculation."""
        sample_task.started_at = datetime.now(timezone.utc)
        sample_task.completed_at = sample_task.started_at + timedelta(seconds=1)
        
        assert sample_task.duration_ms is not None
        assert abs(sample_task.duration_ms - 1000) < 10


class TestLoadedModel:
    """Test LoadedModel dataclass."""
    
    def test_defaults(self, sample_model):
        """Test default values."""
        assert sample_model.use_count == 0
        assert sample_model.is_lightweight is False


# =============================================================================
# Test Resource Monitor
# =============================================================================

class TestResourceMonitor:
    """Test resource monitor."""
    
    def test_get_current_metrics(self, resource_monitor):
        """Test getting current metrics."""
        metrics = resource_monitor.get_current_metrics()
        
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
    
    def test_set_metrics(self, resource_monitor):
        """Test setting metrics."""
        custom = ResourceMetrics(cpu_percent=75.0, memory_percent=80.0)
        resource_monitor.set_metrics(custom)
        
        assert resource_monitor._current_metrics.cpu_percent == 75.0
    
    def test_is_overloaded_false(self, resource_monitor):
        """Test system not overloaded."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
        ))
        
        assert resource_monitor.is_overloaded() is False
    
    def test_is_overloaded_true(self, resource_monitor):
        """Test system overloaded."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=96.0,
            memory_percent=50.0,
        ))
        
        assert resource_monitor.is_overloaded() is True
    
    def test_should_throttle_false(self, resource_monitor):
        """Test no throttling needed."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
        ))
        
        assert resource_monitor.should_throttle() is False
    
    def test_should_throttle_true(self, resource_monitor):
        """Test throttling needed."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=85.0,
            memory_percent=50.0,
        ))
        
        assert resource_monitor.should_throttle() is True
    
    def test_activate_kill_switch(self, resource_monitor, sample_task):
        """Test kill switch activation."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        resource_monitor.register_task(sample_task)
        
        cancelled = resource_monitor.activate_kill_switch()
        
        assert resource_monitor.is_kill_switch_active()
        assert sample_task.task_id in cancelled
        assert sample_task.status == TaskStatus.CANCELLED
    
    def test_deactivate_kill_switch(self, resource_monitor):
        """Test kill switch deactivation."""
        resource_monitor.activate_kill_switch()
        resource_monitor.deactivate_kill_switch()
        
        assert resource_monitor.is_kill_switch_active() is False
    
    def test_can_start_task_kill_switch_active(self, resource_monitor, sample_task):
        """Test cannot start task when kill switch active."""
        resource_monitor.activate_kill_switch()
        
        can_start, reason = resource_monitor.can_start_task(sample_task)
        
        assert can_start is False
        assert "kill switch" in reason.lower()
    
    def test_can_start_task_overloaded(self, resource_monitor, sample_task):
        """Test cannot start task when overloaded."""
        resource_monitor.set_metrics(ResourceMetrics(cpu_percent=96.0))
        
        can_start, reason = resource_monitor.can_start_task(sample_task)
        
        assert can_start is False
        assert "overloaded" in reason.lower()
    
    def test_can_start_task_throttled_low_priority(self, resource_monitor):
        """Test low priority task throttled."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=85.0,
            memory_available_mb=8000,
        ))
        
        task = AITask(
            task_id="low-001",
            name="Background Task",
            priority=TaskPriority.LOW,
        )
        
        can_start, reason = resource_monitor.can_start_task(task)
        
        assert can_start is False
        assert "throttled" in reason.lower()
    
    def test_can_start_task_throttled_high_priority(self, resource_monitor):
        """Test high priority task not throttled."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=85.0,
            memory_available_mb=8000,
        ))
        
        task = AITask(
            task_id="high-001",
            name="Critical Task",
            priority=TaskPriority.HIGH,
        )
        
        can_start, _ = resource_monitor.can_start_task(task)
        
        assert can_start is True
    
    def test_register_task(self, resource_monitor, sample_task):
        """Test task registration."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        
        result = resource_monitor.register_task(sample_task)
        
        assert result is True
        assert sample_task.status == TaskStatus.RUNNING
        assert sample_task.started_at is not None
    
    def test_complete_task(self, resource_monitor, sample_task):
        """Test task completion."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        resource_monitor.register_task(sample_task)
        
        resource_monitor.complete_task(sample_task.task_id, success=True)
        
        assert sample_task.status == TaskStatus.COMPLETED
        assert sample_task.completed_at is not None
    
    def test_complete_task_failed(self, resource_monitor, sample_task):
        """Test task failure."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        resource_monitor.register_task(sample_task)
        
        resource_monitor.complete_task(
            sample_task.task_id,
            success=False,
            error="Out of memory",
        )
        
        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error == "Out of memory"
    
    def test_get_running_tasks(self, resource_monitor, sample_task):
        """Test getting running tasks."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        resource_monitor.register_task(sample_task)
        
        running = resource_monitor.get_running_tasks()
        
        assert len(running) == 1
        assert running[0].task_id == sample_task.task_id


# =============================================================================
# Test Model Manager
# =============================================================================

class TestModelManager:
    """Test model manager."""
    
    def test_initial_state(self, model_manager):
        """Test initial state."""
        assert model_manager.total_memory_used == 0
        assert model_manager.available_memory == 4000
    
    def test_load_model(self, model_manager, sample_model):
        """Test loading a model."""
        result = model_manager.load_model(sample_model)
        
        assert result is True
        assert model_manager.total_memory_used == 500
    
    def test_load_model_already_loaded(self, model_manager, sample_model):
        """Test loading already loaded model."""
        model_manager.load_model(sample_model)
        result = model_manager.load_model(sample_model)
        
        assert result is True
        assert model_manager.total_memory_used == 500  # Not doubled
    
    def test_load_model_insufficient_memory(self, model_manager):
        """Test loading model with insufficient memory."""
        large_model = LoadedModel(
            model_id="large",
            name="large-model",
            memory_mb=5000,  # More than max
        )
        
        result = model_manager.load_model(large_model)
        
        assert result is False
    
    def test_unload_model(self, model_manager, sample_model):
        """Test unloading a model."""
        model_manager.load_model(sample_model)
        result = model_manager.unload_model(sample_model.model_id)
        
        assert result is True
        assert model_manager.total_memory_used == 0
    
    def test_unload_model_not_loaded(self, model_manager):
        """Test unloading non-existent model."""
        result = model_manager.unload_model("nonexistent")
        
        assert result is False
    
    def test_get_model(self, model_manager, sample_model):
        """Test getting a loaded model."""
        model_manager.load_model(sample_model)
        
        model = model_manager.get_model(sample_model.model_id)
        
        assert model is not None
        assert model.use_count == 1
    
    def test_get_model_not_loaded(self, model_manager):
        """Test getting non-loaded model."""
        model = model_manager.get_model("nonexistent")
        
        assert model is None
    
    def test_register_fallback(self, model_manager):
        """Test registering fallback."""
        model_manager.register_fallback("full-model", "lite-model")
        
        fallback = model_manager.get_fallback("full-model")
        assert fallback == "lite-model"
    
    def test_switch_to_fallback(self, model_manager, sample_model):
        """Test switching to fallback."""
        model_manager.load_model(sample_model)
        model_manager.register_fallback(sample_model.model_id, "model-001-lite")
        
        result = model_manager.switch_to_fallback(sample_model.model_id)
        
        assert result is True
        assert model_manager.get_model(sample_model.model_id) is None
        assert model_manager.get_model("model-001-lite") is not None
    
    def test_get_loaded_models(self, model_manager, sample_model):
        """Test getting all loaded models."""
        model_manager.load_model(sample_model)
        
        models = model_manager.get_loaded_models()
        
        assert len(models) == 1


# =============================================================================
# Test PII Redactor
# =============================================================================

class TestPIIRedactor:
    """Test PII redactor."""
    
    def test_detect_email(self, pii_redactor):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info."
        
        result = pii_redactor.redact(text, [PIIType.EMAIL])
        
        assert "john.doe@example.com" not in result.redacted_text
        assert PIIType.EMAIL.value in result.pii_counts
        assert result.pii_counts[PIIType.EMAIL.value] == 1
    
    def test_detect_phone(self, pii_redactor):
        """Test phone detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543."
        
        result = pii_redactor.redact(text, [PIIType.PHONE])
        
        assert "555-123-4567" not in result.redacted_text
        assert "987-6543" not in result.redacted_text
        assert result.pii_counts.get(PIIType.PHONE.value, 0) >= 2
    
    def test_detect_ssn(self, pii_redactor):
        """Test SSN detection."""
        text = "SSN: 123-45-6789"
        
        result = pii_redactor.redact(text, [PIIType.SSN])
        
        assert "123-45-6789" not in result.redacted_text
        assert PIIType.SSN.value in result.pii_counts
    
    def test_detect_credit_card(self, pii_redactor):
        """Test credit card detection."""
        text = "Card: 4111-2222-3333-4444"
        
        result = pii_redactor.redact(text, [PIIType.CREDIT_CARD])
        
        assert "4111-2222-3333-4444" not in result.redacted_text
        assert PIIType.CREDIT_CARD.value in result.pii_counts
    
    def test_detect_name_with_prefix(self, pii_redactor):
        """Test name detection with prefix."""
        text = "Dear Mr. John Smith, thank you for your inquiry."
        
        result = pii_redactor.redact(text, [PIIType.NAME])
        
        # Name should be redacted
        assert result.pii_counts.get(PIIType.NAME.value, 0) >= 1
    
    def test_redaction_masked(self, pii_redactor):
        """Test masked redaction."""
        text = "Email: test@example.com"
        
        result = pii_redactor.redact(
            text,
            [PIIType.EMAIL],
            method=RedactionMethod.MASKED,
        )
        
        assert "test@example.com" not in result.redacted_text
        assert "*" in result.redacted_text
    
    def test_redaction_replaced(self, pii_redactor):
        """Test replaced redaction."""
        text = "Email: test@example.com"
        
        result = pii_redactor.redact(
            text,
            [PIIType.EMAIL],
            method=RedactionMethod.REPLACED,
        )
        
        assert "[REDACTED_" in result.redacted_text
    
    def test_redaction_hashed(self, pii_redactor):
        """Test hashed redaction."""
        text = "Email: test@example.com"
        
        result = pii_redactor.redact(
            text,
            [PIIType.EMAIL],
            method=RedactionMethod.HASHED,
        )
        
        # Hash is 16 hex chars
        assert len(result.redacted_text) > 0
        assert "@" not in result.redacted_text
    
    def test_redact_all_types(self, pii_redactor):
        """Test redacting all PII types."""
        text = """
        Contact: john.doe@example.com
        Phone: 555-123-4567
        Dear Mr. Smith
        """
        
        result = pii_redactor.redact(text)
        
        assert "john.doe@example.com" not in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
    
    def test_rehydrate_authorized(self, pii_redactor):
        """Test re-hydration for authorized user."""
        text = "Email: test@example.com"
        
        result = pii_redactor.redact(
            text,
            [PIIType.EMAIL],
            method=RedactionMethod.REPLACED,
        )
        
        rehydrated = pii_redactor.rehydrate(result.redacted_text, authorized=True)
        
        assert "test@example.com" in rehydrated
    
    def test_rehydrate_unauthorized(self, pii_redactor):
        """Test re-hydration blocked for unauthorized."""
        text = "Email: test@example.com"
        
        result = pii_redactor.redact(
            text,
            [PIIType.EMAIL],
            method=RedactionMethod.REPLACED,
        )
        
        rehydrated = pii_redactor.rehydrate(result.redacted_text, authorized=False)
        
        assert "test@example.com" not in rehydrated
        assert "[REDACTED_" in rehydrated
    
    def test_audit_log(self, pii_redactor):
        """Test audit log creation."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        
        result = pii_redactor.redact(text, [PIIType.EMAIL, PIIType.PHONE])
        
        audit = pii_redactor.get_audit_log(result.result_id)
        
        assert len(audit) >= 2
        assert all(e.result_id == result.result_id for e in audit)
    
    def test_no_pii_found(self, pii_redactor):
        """Test text with no PII."""
        text = "Hello, this is a normal message with no personal data."
        
        result = pii_redactor.redact(text)
        
        assert result.redacted_text == text
        assert len(result.matches) == 0


# =============================================================================
# Test HITL Consistency Monitor
# =============================================================================

class TestHITLConsistencyMonitor:
    """Test HITL consistency monitor."""
    
    def test_record_feedback(self, hitl_monitor):
        """Test recording feedback."""
        feedback = SuggestionFeedback(
            feedback_id="fb-001",
            suggestion_id="sug-001",
            model_name="test-model",
            accepted=True,
        )
        
        hitl_monitor.record_feedback(feedback)
        
        assert len(hitl_monitor._feedback) == 1
    
    def test_calculate_drift_no_data(self, hitl_monitor):
        """Test drift calculation with no data."""
        drift = hitl_monitor.calculate_drift("test-model")
        
        assert drift.total_suggestions == 0
        assert drift.severity == DriftSeverity.NONE
    
    def test_calculate_drift_low_corrections(self, hitl_monitor):
        """Test drift with few corrections."""
        for i in range(10):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"fb-{i}",
                suggestion_id=f"sug-{i}",
                model_name="test-model",
                accepted=True,
                corrected=False,
            ))
        
        drift = hitl_monitor.calculate_drift("test-model")
        
        assert drift.correction_rate == 0.0
        assert drift.severity == DriftSeverity.NONE
    
    def test_calculate_drift_high_corrections(self, hitl_monitor):
        """Test drift with many corrections."""
        for i in range(10):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"fb-{i}",
                suggestion_id=f"sug-{i}",
                model_name="test-model",
                accepted=False,
                corrected=True,
                correction_magnitude=0.8,
            ))
        
        drift = hitl_monitor.calculate_drift("test-model")
        
        assert drift.correction_rate == 1.0
        assert drift.severity == DriftSeverity.CRITICAL
    
    def test_register_prompt_variant(self, hitl_monitor):
        """Test registering prompt variant."""
        variant = PromptVariant(
            variant_id="v1",
            name="Formal",
            prompt_template="Please provide: {input}",
        )
        
        hitl_monitor.register_prompt_variant(variant)
        
        assert "v1" in hitl_monitor._prompt_variants
    
    def test_select_prompt_variant(self, hitl_monitor):
        """Test selecting prompt variant."""
        variants = [
            PromptVariant(
                variant_id="v1",
                name="Formal",
                prompt_template="Template 1",
                weight=1.0,
            ),
            PromptVariant(
                variant_id="v2",
                name="Casual",
                prompt_template="Template 2",
                weight=1.0,
            ),
        ]
        
        for v in variants:
            hitl_monitor.register_prompt_variant(v)
        
        selected = hitl_monitor.select_prompt_variant()
        
        assert selected is not None
        assert selected.variant_id in ["v1", "v2"]
    
    def test_select_specific_variants(self, hitl_monitor):
        """Test selecting from specific variants."""
        variants = [
            PromptVariant(variant_id="v1", name="A", prompt_template="T1"),
            PromptVariant(variant_id="v2", name="B", prompt_template="T2"),
            PromptVariant(variant_id="v3", name="C", prompt_template="T3"),
        ]
        
        for v in variants:
            hitl_monitor.register_prompt_variant(v)
        
        selected = hitl_monitor.select_prompt_variant(["v1", "v2"])
        
        assert selected is not None
        assert selected.variant_id in ["v1", "v2"]
    
    def test_update_variant_performance_accepted(self, hitl_monitor):
        """Test updating variant performance on acceptance."""
        variant = PromptVariant(
            variant_id="v1",
            name="Test",
            prompt_template="T",
            acceptance_rate=0.5,
            weight=1.0,
        )
        hitl_monitor.register_prompt_variant(variant)
        
        hitl_monitor.update_variant_performance("v1", accepted=True)
        
        assert hitl_monitor._prompt_variants["v1"].acceptance_rate > 0.5
    
    def test_update_variant_performance_rejected(self, hitl_monitor):
        """Test updating variant performance on rejection."""
        variant = PromptVariant(
            variant_id="v1",
            name="Test",
            prompt_template="T",
            acceptance_rate=0.5,
            weight=1.0,
        )
        hitl_monitor.register_prompt_variant(variant)
        
        hitl_monitor.update_variant_performance("v1", accepted=False)
        
        assert hitl_monitor._prompt_variants["v1"].acceptance_rate < 0.5
    
    def test_calculate_consistency_score_no_data(self, hitl_monitor):
        """Test consistency score with no data."""
        score = hitl_monitor.calculate_consistency_score("test-model")
        
        assert score.score == 100.0
        assert score.total == 0
    
    def test_calculate_consistency_score_with_data(self, hitl_monitor):
        """Test consistency score calculation."""
        # Add 8 accepted, 2 corrected
        for i in range(8):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"fb-{i}",
                suggestion_id=f"sug-{i}",
                model_name="test-model",
                accepted=True,
            ))
        
        for i in range(2):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"fb-corr-{i}",
                suggestion_id=f"sug-corr-{i}",
                model_name="test-model",
                accepted=False,
                corrected=True,
                correction_magnitude=0.5,
            ))
        
        score = hitl_monitor.calculate_consistency_score("test-model")
        
        assert score.total == 10
        assert score.accepted == 8
        assert score.corrected == 2
        assert score.score > 0
    
    def test_get_variant_performance(self, hitl_monitor):
        """Test getting variant performance."""
        variant = PromptVariant(
            variant_id="v1",
            name="Test",
            prompt_template="T",
            total_uses=10,
            acceptance_rate=0.8,
        )
        hitl_monitor.register_prompt_variant(variant)
        
        performance = hitl_monitor.get_variant_performance()
        
        assert len(performance) == 1
        assert performance[0]["variant_id"] == "v1"
        assert performance[0]["total_uses"] == 10


# =============================================================================
# Test Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_resource_monitor(self):
        """Test creating resource monitor."""
        monitor = create_resource_monitor()
        
        assert monitor is not None
        assert monitor._kill_threshold == KILL_SWITCH_THRESHOLD
    
    def test_create_resource_monitor_custom(self):
        """Test creating monitor with custom thresholds."""
        monitor = create_resource_monitor(kill_threshold=90.0)
        
        assert monitor._kill_threshold == 90.0
    
    def test_create_model_manager(self):
        """Test creating model manager."""
        manager = create_model_manager()
        
        assert manager is not None
        assert manager._max_memory_mb == 8000
    
    def test_create_pii_redactor(self):
        """Test creating PII redactor."""
        redactor = create_pii_redactor()
        
        assert redactor is not None
    
    def test_create_hitl_monitor(self):
        """Test creating HITL monitor."""
        monitor = create_hitl_monitor()
        
        assert monitor is not None


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_text_redaction(self, pii_redactor):
        """Test redacting empty text."""
        result = pii_redactor.redact("")
        
        assert result.redacted_text == ""
        assert len(result.matches) == 0
    
    def test_multiple_same_email(self, pii_redactor):
        """Test multiple occurrences of same email."""
        text = "Email: test@test.com, also test@test.com"
        
        result = pii_redactor.redact(text, [PIIType.EMAIL])
        
        assert "test@test.com" not in result.redacted_text
        assert result.pii_counts.get(PIIType.EMAIL.value, 0) == 2
    
    def test_model_usage_tracking(self, model_manager, sample_model):
        """Test model usage is tracked."""
        model_manager.load_model(sample_model)
        
        model_manager.get_model(sample_model.model_id)
        model_manager.get_model(sample_model.model_id)
        model_manager.get_model(sample_model.model_id)
        
        model = model_manager.get_model(sample_model.model_id)
        assert model.use_count == 4
    
    def test_drift_severity_boundaries(self, hitl_monitor):
        """Test drift severity boundaries."""
        # 15% correction rate = LOW
        for i in range(85):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"acc-{i}",
                suggestion_id=f"sug-{i}",
                model_name="test",
                accepted=True,
            ))
        for i in range(15):
            hitl_monitor.record_feedback(SuggestionFeedback(
                feedback_id=f"corr-{i}",
                suggestion_id=f"sug-corr-{i}",
                model_name="test",
                corrected=True,
            ))
        
        drift = hitl_monitor.calculate_drift("test")
        
        assert drift.severity == DriftSeverity.LOW
    
    def test_task_insufficient_memory(self, resource_monitor):
        """Test task blocked for insufficient memory."""
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=100,
        ))
        
        task = AITask(
            task_id="big",
            name="Big Task",
            priority=TaskPriority.HIGH,
            estimated_memory_mb=200,  # Need 200, have 100, 200 > 100 * 0.5
        )
        
        can_start, reason = resource_monitor.can_start_task(task)
        
        assert can_start is False
        assert "memory" in reason.lower()


# =============================================================================
# Test Integration
# =============================================================================

class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_resource_lifecycle(self, resource_monitor, sample_task):
        """Test complete resource monitoring lifecycle."""
        # Set normal conditions
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=50.0,
            memory_available_mb=8000,
        ))
        
        # Start task
        assert resource_monitor.register_task(sample_task)
        assert sample_task.status == TaskStatus.RUNNING
        
        # Simulate load increase
        resource_monitor.set_metrics(ResourceMetrics(
            cpu_percent=96.0,
            memory_available_mb=8000,
        ))
        
        # Kill switch
        cancelled = resource_monitor.activate_kill_switch()
        assert sample_task.task_id in cancelled
        
        # Deactivate
        resource_monitor.deactivate_kill_switch()
        resource_monitor.set_metrics(ResourceMetrics(cpu_percent=50.0))
        
        assert not resource_monitor.is_kill_switch_active()
    
    def test_model_fallback_chain(self, model_manager):
        """Test model fallback workflow."""
        # Load main model
        main = LoadedModel(
            model_id="main-model",
            name="Main LLM",
            memory_mb=2000,
        )
        model_manager.load_model(main)
        model_manager.register_fallback("main-model", "lite-model")
        
        # Switch to fallback
        model_manager.switch_to_fallback("main-model")
        
        # Lite model should be loaded
        lite = model_manager.get_model("lite-model")
        assert lite is not None
        assert lite.is_lightweight
        
        # Main should be unloaded
        assert model_manager.get_model("main-model") is None
    
    def test_pii_full_workflow(self, pii_redactor):
        """Test complete PII workflow."""
        original = "Dear Mr. John Doe, your email is john@company.com and phone is 555-123-4567."
        
        # Redact
        result = pii_redactor.redact(
            original,
            method=RedactionMethod.REPLACED,
        )
        
        # Verify redacted
        assert "john@company.com" not in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
        
        # Audit log exists
        audit = pii_redactor.get_audit_log(result.result_id)
        assert len(audit) >= 2
        
        # Re-hydrate
        restored = pii_redactor.rehydrate(result.redacted_text, authorized=True)
        assert "john@company.com" in restored
        assert "555-123-4567" in restored

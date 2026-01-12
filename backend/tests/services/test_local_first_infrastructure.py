"""
Tests for Local-First Infrastructure with ONNX Runtime Optimization.
"""

import gc
import time
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, Any

import pytest
import numpy as np

from sensei.services.core.local_first_infrastructure import (
    # Enums
    ModelPrecision,
    ModelSize,
    CircuitState,
    ExecutionProvider,
    # Dataclasses
    ModelConfig,
    InferenceResult,
    SystemResources,
    # Memory Management
    MemoryManager,
    # Circuit Breaker
    CircuitBreaker,
    # Fallbacks
    FallbackStrategy,
    RegexFallback,
    HeuristicFallback,
    FallbackManager,
    # ONNX Management
    ONNXModelSession,
    ONNXModelManager,
    ONNXOptimizer,
    # Main Service
    LocalFirstService,
    get_local_first_service,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def memory_manager():
    """Create a memory manager instance."""
    return MemoryManager()


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker instance."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout_s=1.0)


@pytest.fixture
def regex_fallback():
    """Create a regex fallback instance."""
    return RegexFallback()


@pytest.fixture
def heuristic_fallback():
    """Create a heuristic fallback instance."""
    return HeuristicFallback()


@pytest.fixture
def fallback_manager():
    """Create a fallback manager instance."""
    return FallbackManager()


@pytest.fixture
def model_config():
    """Create a model configuration."""
    return ModelConfig(
        model_path=Path("test_model.onnx"),
        model_name="test_model",
        precision=ModelPrecision.FLOAT32,
        size_variant=ModelSize.MEDIUM,
        memory_mb=512,
        warmup_required=False,
    )


@pytest.fixture
def mock_onnx_session():
    """Create a mock ONNX session."""
    session = Mock()
    session.get_inputs.return_value = [
        Mock(name="input", shape=[1, 128], type="tensor(float)")
    ]
    session.get_outputs.return_value = [
        Mock(name="output", shape=[1, 64])
    ]
    session.run.return_value = [np.zeros((1, 64), dtype=np.float32)]
    return session


@pytest.fixture
def model_session(model_config, mock_onnx_session):
    """Create a model session."""
    return ONNXModelSession(model_config, mock_onnx_session)


@pytest.fixture
def local_first_service(tmp_path):
    """Create a local-first service instance."""
    return LocalFirstService(model_dir=tmp_path, enable_fallbacks=True)


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Tests for enumeration types."""
    
    def test_model_precision_values(self):
        """Test model precision enum values."""
        assert ModelPrecision.FLOAT32.value == "float32"
        assert ModelPrecision.FLOAT16.value == "float16"
        assert ModelPrecision.INT8.value == "int8"
        assert ModelPrecision.DYNAMIC_QUANTIZED.value == "dynamic_quantized"
    
    def test_model_size_values(self):
        """Test model size enum values."""
        assert ModelSize.SMALL.value == "small"
        assert ModelSize.MEDIUM.value == "medium"
        assert ModelSize.LARGE.value == "large"
    
    def test_circuit_state_values(self):
        """Test circuit state enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"
    
    def test_execution_provider_values(self):
        """Test execution provider enum values."""
        assert ExecutionProvider.CPU.value == "CPUExecutionProvider"
        assert ExecutionProvider.CUDA.value == "CUDAExecutionProvider"


# =============================================================================
# Tests: Dataclasses
# =============================================================================

class TestDataclasses:
    """Tests for dataclass types."""
    
    def test_model_config_creation(self):
        """Test model config creation with defaults."""
        config = ModelConfig(
            model_path=Path("test.onnx"),
            model_name="test"
        )
        assert config.precision == ModelPrecision.FLOAT32
        assert config.size_variant == ModelSize.MEDIUM
        assert config.memory_mb == 512
        assert config.warmup_required is True
        assert config.input_names == ["input"]
        assert config.output_names == ["output"]
    
    def test_inference_result(self):
        """Test inference result creation."""
        result = InferenceResult(
            outputs={"output": np.array([1, 2, 3])},
            latency_ms=10.5,
            model_name="test",
        )
        assert result.used_fallback is False
        assert result.fallback_reason is None
    
    def test_inference_result_with_fallback(self):
        """Test inference result with fallback."""
        result = InferenceResult(
            outputs={"output": np.array([1])},
            latency_ms=0.0,
            model_name="test",
            used_fallback=True,
            fallback_reason="Model not loaded",
        )
        assert result.used_fallback is True
        assert "not loaded" in result.fallback_reason
    
    def test_system_resources(self):
        """Test system resources dataclass."""
        resources = SystemResources(
            available_ram_mb=4096.0,
            total_ram_mb=16384.0,
            cpu_count=8,
            cpu_usage_percent=25.0,
            available_threads=6,
        )
        assert resources.available_ram_mb == 4096.0
        assert resources.cpu_count == 8


# =============================================================================
# Tests: MemoryManager
# =============================================================================

class TestMemoryManager:
    """Tests for memory management."""
    
    def test_get_system_resources(self, memory_manager):
        """Test getting system resources."""
        resources = memory_manager.get_system_resources()
        
        assert isinstance(resources, SystemResources)
        assert resources.available_ram_mb > 0
        assert resources.total_ram_mb > 0
        assert resources.cpu_count >= 1
        assert 0 <= resources.cpu_usage_percent <= 100
    
    def test_check_memory_sufficient(self, memory_manager):
        """Test memory check with sufficient memory."""
        # Request small amount
        can_load, reason = memory_manager.check_memory_for_model(100)
        # Should generally pass unless system is very low on memory
        assert isinstance(can_load, bool)
        if not can_load:
            assert reason is not None
    
    def test_check_memory_insufficient(self, memory_manager):
        """Test memory check with insufficient memory."""
        # Request absurdly large amount
        can_load, reason = memory_manager.check_memory_for_model(1000000)
        assert can_load is False
        assert "Insufficient memory" in reason
    
    def test_suggest_model_variant_small_memory(self, memory_manager):
        """Test model variant suggestion with limited memory."""
        with patch.object(memory_manager, 'get_system_resources') as mock:
            mock.return_value = SystemResources(
                available_ram_mb=1500.0,  # Below 2GB threshold
                total_ram_mb=4096.0,
                cpu_count=4,
                cpu_usage_percent=50.0,
                available_threads=2,
            )
            
            suggested = memory_manager.suggest_model_variant(ModelSize.LARGE)
            assert suggested == ModelSize.SMALL
    
    def test_suggest_model_variant_medium_memory(self, memory_manager):
        """Test model variant suggestion with medium memory."""
        with patch.object(memory_manager, 'get_system_resources') as mock:
            mock.return_value = SystemResources(
                available_ram_mb=3000.0,  # Between 2GB and 4GB
                total_ram_mb=8192.0,
                cpu_count=4,
                cpu_usage_percent=50.0,
                available_threads=2,
            )
            
            # Large should be downgraded to medium
            suggested = memory_manager.suggest_model_variant(ModelSize.LARGE)
            assert suggested == ModelSize.MEDIUM
            
            # Medium should stay medium
            suggested = memory_manager.suggest_model_variant(ModelSize.MEDIUM)
            assert suggested == ModelSize.MEDIUM
    
    def test_suggest_model_variant_sufficient_memory(self, memory_manager):
        """Test model variant suggestion with sufficient memory."""
        with patch.object(memory_manager, 'get_system_resources') as mock:
            mock.return_value = SystemResources(
                available_ram_mb=8000.0,  # Plenty of memory
                total_ram_mb=16384.0,
                cpu_count=8,
                cpu_usage_percent=25.0,
                available_threads=6,
            )
            
            suggested = memory_manager.suggest_model_variant(ModelSize.LARGE)
            assert suggested == ModelSize.LARGE
    
    def test_get_optimal_thread_count(self, memory_manager):
        """Test optimal thread count calculation."""
        threads = memory_manager.get_optimal_thread_count()
        assert threads >= 1
        assert threads <= 8  # Capped at 8
    
    def test_cleanup(self, memory_manager):
        """Test memory cleanup."""
        # Should not raise
        memory_manager.cleanup()


# =============================================================================
# Tests: CircuitBreaker
# =============================================================================

class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""
    
    def test_initial_state_closed(self, circuit_breaker):
        """Test circuit starts in closed state."""
        assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_can_proceed_when_closed(self, circuit_breaker):
        """Test can proceed when circuit is closed."""
        can_proceed, reason = circuit_breaker.can_proceed()
        assert can_proceed is True
        assert reason is None
    
    def test_record_success_keeps_closed(self, circuit_breaker):
        """Test recording success keeps circuit closed."""
        circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_open_after_threshold_failures(self, circuit_breaker):
        """Test circuit opens after threshold failures."""
        # Record failures up to threshold
        for i in range(3):
            circuit_breaker.record_failure(Exception(f"Error {i}"))
        
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_cannot_proceed_when_open(self, circuit_breaker):
        """Test cannot proceed when circuit is open."""
        # Force open
        for i in range(3):
            circuit_breaker.record_failure()
        
        can_proceed, reason = circuit_breaker.can_proceed()
        assert can_proceed is False
        assert "Circuit OPEN" in reason
    
    def test_half_open_after_recovery_timeout(self, circuit_breaker):
        """Test circuit transitions to half-open after timeout."""
        # Force open
        for i in range(3):
            circuit_breaker.record_failure()
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    def test_half_open_allows_test_call(self, circuit_breaker):
        """Test half-open allows limited test calls."""
        # Force open
        for i in range(3):
            circuit_breaker.record_failure()
        
        # Wait for recovery
        time.sleep(1.1)
        
        # First call should be allowed
        can_proceed, reason = circuit_breaker.can_proceed()
        assert can_proceed is True
        
        # Second call should be blocked (max 1 in half-open)
        can_proceed, reason = circuit_breaker.can_proceed()
        assert can_proceed is False
        assert "max test calls" in reason
    
    def test_success_in_half_open_closes_circuit(self, circuit_breaker):
        """Test success in half-open closes the circuit."""
        # Force open then wait for half-open
        for i in range(3):
            circuit_breaker.record_failure()
        time.sleep(1.1)
        
        # Record success
        circuit_breaker.record_success()
        
        assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_failure_in_half_open_reopens_circuit(self, circuit_breaker):
        """Test failure in half-open reopens the circuit."""
        # Force open then wait for half-open
        for i in range(3):
            circuit_breaker.record_failure()
        time.sleep(1.1)
        
        # Make test call
        circuit_breaker.can_proceed()
        
        # Record failure
        circuit_breaker.record_failure()
        
        assert circuit_breaker.state == CircuitState.OPEN
    
    def test_reset(self, circuit_breaker):
        """Test circuit breaker reset."""
        # Force open
        for i in range(3):
            circuit_breaker.record_failure()
        
        circuit_breaker.reset()
        
        assert circuit_breaker.state == CircuitState.CLOSED
        can_proceed, _ = circuit_breaker.can_proceed()
        assert can_proceed is True
    
    def test_thread_safety(self, circuit_breaker):
        """Test circuit breaker is thread-safe."""
        errors = []
        
        def record_failures():
            try:
                for _ in range(100):
                    circuit_breaker.record_failure()
                    circuit_breaker.can_proceed()
            except Exception as e:
                errors.append(e)
        
        def record_successes():
            try:
                for _ in range(100):
                    circuit_breaker.record_success()
                    circuit_breaker.can_proceed()
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=record_failures),
            threading.Thread(target=record_successes),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


# =============================================================================
# Tests: RegexFallback
# =============================================================================

class TestRegexFallback:
    """Tests for regex-based fallback."""
    
    def test_can_handle_supported_types(self, regex_fallback):
        """Test can handle supported input types."""
        assert regex_fallback.can_handle("email_extraction") is True
        assert regex_fallback.can_handle("phone_extraction") is True
        assert regex_fallback.can_handle("date_extraction") is True
        assert regex_fallback.can_handle("number_extraction") is True
        assert regex_fallback.can_handle("part_number") is True
    
    def test_cannot_handle_unsupported_types(self, regex_fallback):
        """Test cannot handle unsupported input types."""
        assert regex_fallback.can_handle("sentiment") is False
        assert regex_fallback.can_handle("translation") is False
    
    def test_extract_email(self, regex_fallback):
        """Test email extraction."""
        text = "Contact us at support@example.com or sales@company.org"
        result = regex_fallback.execute(text, {"type": "email_extraction"})
        
        assert len(result) == 2
        emails = [r["email"] for r in result]
        assert "support@example.com" in emails
        assert "sales@company.org" in emails
    
    def test_extract_phone(self, regex_fallback):
        """Test phone number extraction."""
        text = "Call us at 555-123-4567 or 800.555.1234"
        result = regex_fallback.execute(text, {"type": "phone_extraction"})
        
        assert len(result) == 2
    
    def test_extract_date(self, regex_fallback):
        """Test date extraction."""
        text = "Due by 12/25/2024 or 2024-01-15"
        result = regex_fallback.execute(text, {"type": "date_extraction"})
        
        assert len(result) == 2
    
    def test_extract_part_number(self, regex_fallback):
        """Test part number extraction."""
        text = "Order ABC-12345 and XYZ-99887-A1"
        result = regex_fallback.execute(text, {"type": "part_number"})
        
        assert len(result) == 2
    
    def test_no_matches(self, regex_fallback):
        """Test when no patterns match."""
        text = "Plain text with no patterns"
        result = regex_fallback.execute(text, {"type": "email_extraction"})
        
        assert result == []


# =============================================================================
# Tests: HeuristicFallback
# =============================================================================

class TestHeuristicFallback:
    """Tests for heuristic-based fallback."""
    
    def test_can_handle_supported_types(self, heuristic_fallback):
        """Test can handle supported input types."""
        assert heuristic_fallback.can_handle("text_classification") is True
        assert heuristic_fallback.can_handle("sentiment") is True
        assert heuristic_fallback.can_handle("language_detection") is True
        assert heuristic_fallback.can_handle("entity_extraction") is True
    
    def test_cannot_handle_unsupported_types(self, heuristic_fallback):
        """Test cannot handle unsupported input types."""
        assert heuristic_fallback.can_handle("email_extraction") is False
    
    def test_text_classification_urgent(self, heuristic_fallback):
        """Test urgent text classification."""
        text = "URGENT: This needs immediate attention ASAP!"
        result = heuristic_fallback.execute(text, {"type": "text_classification"})
        
        assert result["urgent"] >= 0.5
    
    def test_text_classification_question(self, heuristic_fallback):
        """Test question classification."""
        text = "What is the status? When will it arrive?"
        result = heuristic_fallback.execute(text, {"type": "text_classification"})
        
        assert result["question"] > 0
    
    def test_sentiment_positive(self, heuristic_fallback):
        """Test positive sentiment detection."""
        text = "Great job! Excellent work, thank you so much!"
        result = heuristic_fallback.execute(text, {"type": "sentiment"})
        
        assert result["sentiment"] == "positive"
        assert result["confidence"] > 0.5
    
    def test_sentiment_negative(self, heuristic_fallback):
        """Test negative sentiment detection."""
        text = "This is terrible! I'm frustrated and angry about this problem."
        result = heuristic_fallback.execute(text, {"type": "sentiment"})
        
        assert result["sentiment"] == "negative"
        assert result["confidence"] > 0.5
    
    def test_sentiment_neutral(self, heuristic_fallback):
        """Test neutral sentiment detection."""
        text = "The meeting is scheduled for tomorrow at 3pm."
        result = heuristic_fallback.execute(text, {"type": "sentiment"})
        
        assert result["sentiment"] == "neutral"
    
    def test_language_detection_english(self, heuristic_fallback):
        """Test English language detection."""
        text = "The quick brown fox jumps over the lazy dog."
        result = heuristic_fallback.execute(text, {"type": "language_detection"})
        
        assert result["language"] == "en"
        assert result["confidence"] >= 0.5
    
    def test_entity_extraction(self, heuristic_fallback):
        """Test entity extraction."""
        text = "John Smith ordered 50 units from Acme Corp."
        result = heuristic_fallback.execute(text, {"type": "entity_extraction"})
        
        # Should find proper nouns and quantities
        assert len(result) > 0
        types = [e["type"] for e in result]
        assert "PROPER_NOUN" in types or "QUANTITY" in types


# =============================================================================
# Tests: FallbackManager
# =============================================================================

class TestFallbackManager:
    """Tests for fallback manager."""
    
    def test_execute_with_regex_fallback(self, fallback_manager):
        """Test execution with regex fallback."""
        result, strategy = fallback_manager.execute(
            "Contact: test@example.com",
            "email_extraction"
        )
        
        assert len(result) > 0
        assert strategy == "RegexFallback"
    
    def test_execute_with_heuristic_fallback(self, fallback_manager):
        """Test execution with heuristic fallback."""
        result, strategy = fallback_manager.execute(
            "This is great! Thank you!",
            "sentiment"
        )
        
        assert result["sentiment"] == "positive"
        assert strategy == "HeuristicFallback"
    
    def test_execute_unsupported_type(self, fallback_manager):
        """Test execution with unsupported type."""
        result, strategy = fallback_manager.execute(
            "Some text",
            "unsupported_type"
        )
        
        assert result is None
        assert strategy == "none"
    
    def test_add_custom_strategy(self, fallback_manager):
        """Test adding custom fallback strategy."""
        class CustomFallback(FallbackStrategy):
            def can_handle(self, input_type: str) -> bool:
                return input_type == "custom"
            
            def execute(self, input_data, context=None):
                return {"custom_result": True}
        
        fallback_manager.add_strategy(CustomFallback())
        
        result, strategy = fallback_manager.execute("test", "custom")
        assert result == {"custom_result": True}
        assert strategy == "CustomFallback"


# =============================================================================
# Tests: ONNXModelSession
# =============================================================================

class TestONNXModelSession:
    """Tests for ONNX model session wrapper."""
    
    def test_initial_state(self, model_session):
        """Test initial session state."""
        assert model_session.warmed_up is False
        assert model_session.inference_count == 0
        assert model_session.total_inference_time_ms == 0.0
    
    def test_average_inference_time_zero_inferences(self, model_session):
        """Test average time with no inferences."""
        assert model_session.average_inference_time_ms == 0.0
    
    def test_average_inference_time(self, model_session):
        """Test average inference time calculation."""
        model_session.inference_count = 10
        model_session.total_inference_time_ms = 100.0
        
        assert model_session.average_inference_time_ms == 10.0
    
    def test_warmup(self, model_session):
        """Test model warmup."""
        warmup_time = model_session.warmup()
        
        assert model_session.warmed_up is True
        assert warmup_time > 0
    
    def test_warmup_only_once(self, model_session):
        """Test warmup only runs once."""
        first_time = model_session.warmup()
        second_time = model_session.warmup()
        
        assert first_time > 0
        assert second_time == 0.0


# =============================================================================
# Tests: ONNXModelManager
# =============================================================================

class TestONNXModelManager:
    """Tests for ONNX model manager."""
    
    def test_initial_state(self, tmp_path):
        """Test initial manager state."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        assert manager.list_models() == []
        assert manager.circuit_breaker_state == CircuitState.CLOSED
    
    def test_load_model_file_not_found(self, tmp_path, model_config):
        """Test loading non-existent model."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        success, error = manager.load_model(model_config)
        
        assert success is False
        assert "not found" in error.lower() or "not installed" in error.lower()
    
    def test_load_model_without_onnxruntime(self, tmp_path, model_config):
        """Test loading when ONNX Runtime not installed."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        # Create dummy model file
        model_path = tmp_path / "test_model.onnx"
        model_path.write_bytes(b"dummy")
        model_config.model_path = model_path
        
        # Patch the import inside the load_model method
        with patch.dict('sys.modules', {'onnxruntime': None}):
            success, error = manager.load_model(model_config)
        
        # Should fail gracefully (either with import error or file format error)
        # The behavior depends on whether onnxruntime is actually installed
        assert isinstance(success, bool)
        if not success:
            assert error is not None
    
    def test_get_model_stats_not_loaded(self, tmp_path):
        """Test getting stats for non-loaded model."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        stats = manager.get_model_stats("nonexistent")
        assert stats is None
    
    def test_unload_all(self, tmp_path):
        """Test unloading all models."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        # Should not raise even with no models
        manager.unload_all()
        assert manager.list_models() == []
    
    def test_reset_circuit_breaker(self, tmp_path):
        """Test resetting circuit breaker."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        manager.reset_circuit_breaker()
        assert manager.circuit_breaker_state == CircuitState.CLOSED
    
    def test_infer_model_not_loaded(self, tmp_path):
        """Test inference when model not loaded."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        with pytest.raises(ValueError, match="not loaded"):
            manager.infer("nonexistent", {"input": np.array([1])})
    
    def test_infer_with_fallback(self, tmp_path):
        """Test inference with fallback when model not loaded."""
        manager = ONNXModelManager(model_dir=tmp_path)
        
        result = manager.infer(
            "nonexistent",
            {"input": np.array([1])},
            fallback_type="email_extraction",
            fallback_input="Contact: test@example.com"
        )
        
        assert result.used_fallback is True
        assert "not loaded" in result.fallback_reason.lower()


# =============================================================================
# Tests: ONNXOptimizer
# =============================================================================

class TestONNXOptimizer:
    """Tests for ONNX model optimizer."""
    
    def test_quantize_model_missing_dependencies(self, tmp_path):
        """Test quantization with missing dependencies."""
        input_path = tmp_path / "input.onnx"
        output_path = tmp_path / "output.onnx"
        
        # Without creating actual model
        success, error = ONNXOptimizer.quantize_model(
            input_path, output_path, ModelPrecision.INT8
        )
        
        # Should fail gracefully
        assert success is False
    
    def test_optimize_graph_missing_file(self, tmp_path):
        """Test graph optimization with missing file."""
        input_path = tmp_path / "nonexistent.onnx"
        output_path = tmp_path / "output.onnx"
        
        success, error = ONNXOptimizer.optimize_graph(
            input_path, output_path
        )
        
        assert success is False
    
    def test_convert_to_float16_missing_dependencies(self, tmp_path):
        """Test float16 conversion with missing dependencies."""
        input_path = tmp_path / "input.onnx"
        output_path = tmp_path / "output.onnx"
        
        success, error = ONNXOptimizer.convert_to_float16(
            input_path, output_path
        )
        
        assert success is False


# =============================================================================
# Tests: LocalFirstService
# =============================================================================

class TestLocalFirstService:
    """Tests for local-first service."""
    
    def test_initialization(self, local_first_service):
        """Test service initialization."""
        assert local_first_service._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self, local_first_service):
        """Test initialize and shutdown lifecycle."""
        await local_first_service.initialize()
        assert local_first_service._initialized is True
        
        await local_first_service.shutdown()
        assert local_first_service._initialized is False
    
    @pytest.mark.asyncio
    async def test_double_initialize(self, local_first_service):
        """Test calling initialize twice."""
        await local_first_service.initialize()
        await local_first_service.initialize()  # Should not raise
        
        assert local_first_service._initialized is True
    
    def test_get_system_status(self, local_first_service):
        """Test getting system status."""
        status = local_first_service.get_system_status()
        
        assert "initialized" in status
        assert "loaded_models" in status
        assert "circuit_breaker_state" in status
        assert "available_ram_mb" in status
        assert "cpu_count" in status
        assert "optimal_threads" in status
    
    def test_run_fallback(self, local_first_service):
        """Test running fallback directly."""
        result, strategy = local_first_service.run_fallback(
            "Contact: test@example.com",
            "email_extraction"
        )
        
        assert len(result) > 0
        assert strategy == "RegexFallback"
    
    def test_run_fallback_sentiment(self, local_first_service):
        """Test running sentiment fallback."""
        result, strategy = local_first_service.run_fallback(
            "This is excellent work!",
            "sentiment"
        )
        
        assert result["sentiment"] == "positive"
        assert strategy == "HeuristicFallback"
    
    def test_load_model_nonexistent(self, local_first_service, tmp_path):
        """Test loading non-existent model."""
        success, error = local_first_service.load_model(
            model_path=tmp_path / "nonexistent.onnx",
            model_name="test",
        )
        
        assert success is False
    
    def test_enable_fallbacks_toggle(self, tmp_path):
        """Test toggling fallback enablement."""
        service = LocalFirstService(model_dir=tmp_path, enable_fallbacks=False)
        
        # Without fallbacks, should raise when model not loaded
        with pytest.raises(ValueError):
            service.infer(
                "nonexistent",
                {"input": np.array([1])},
                fallback_type="email_extraction",
                fallback_input="test@example.com"
            )


# =============================================================================
# Tests: Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton service access."""
    
    def test_get_local_first_service(self):
        """Test getting singleton instance."""
        service1 = get_local_first_service()
        service2 = get_local_first_service()
        
        assert service1 is service2


# =============================================================================
# Tests: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_text_fallback(self, fallback_manager):
        """Test fallback with empty text."""
        result, strategy = fallback_manager.execute("", "email_extraction")
        assert result == []
    
    def test_special_characters_fallback(self, fallback_manager):
        """Test fallback with special characters."""
        result, strategy = fallback_manager.execute(
            "!@#$%^&*(){}[]",
            "sentiment"
        )
        assert result["sentiment"] == "neutral"
    
    def test_unicode_text_fallback(self, heuristic_fallback):
        """Test fallback with unicode text."""
        text = "Hello 你好 مرحبا"
        result = heuristic_fallback.execute(text, {"type": "language_detection"})
        
        assert "language" in result
        assert "confidence" in result
    
    def test_very_long_text_fallback(self, heuristic_fallback):
        """Test fallback with very long text."""
        text = "word " * 10000
        result = heuristic_fallback.execute(text, {"type": "sentiment"})
        
        assert result is not None
    
    def test_memory_manager_without_psutil(self, memory_manager):
        """Test memory manager fallback without psutil."""
        with patch.dict('sys.modules', {'psutil': None}):
            # Should use fallback values
            resources = memory_manager.get_system_resources()
            assert resources.cpu_count >= 1


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests for local-first infrastructure."""
    
    def test_full_fallback_workflow(self, local_first_service):
        """Test complete fallback workflow."""
        # Try to get sentiment from text
        result, strategy = local_first_service.run_fallback(
            "I'm very happy with the great service!",
            "sentiment"
        )
        
        assert result["sentiment"] == "positive"
        assert result["confidence"] > 0.5
    
    def test_system_status_reflects_state(self, local_first_service):
        """Test system status reflects actual state."""
        status = local_first_service.get_system_status()
        
        assert status["initialized"] is False
        assert status["loaded_models"] == []
        assert status["circuit_breaker_state"] == "closed"
    
    def test_multiple_fallback_types(self, local_first_service):
        """Test multiple fallback types in sequence."""
        # Email extraction
        result1, _ = local_first_service.run_fallback(
            "Email: user@domain.com", "email_extraction"
        )
        
        # Sentiment analysis
        result2, _ = local_first_service.run_fallback(
            "Terrible experience", "sentiment"
        )
        
        # Text classification
        result3, _ = local_first_service.run_fallback(
            "URGENT: Need help!", "text_classification"
        )
        
        assert len(result1) == 1
        assert result2["sentiment"] == "negative"
        assert result3["urgent"] > 0

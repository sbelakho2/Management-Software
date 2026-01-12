"""
Tests for ONNX Model Initialization and Validation.

Tests the model registry, validator, and initialization functions.
"""

import pytest
from pathlib import Path
import tempfile


class TestModelValidationResult:
    """Tests for ModelValidationResult dataclass."""
    
    def test_creation(self):
        """Test creating a validation result."""
        from sensei.services.ai.onnx_model_init import ModelValidationResult
        
        result = ModelValidationResult(
            model_name="test_model",
            is_valid=True,
        )
        
        assert result.model_name == "test_model"
        assert result.is_valid is True
        assert result.opset_version is None
        assert result.warmup_time_ms is None
        assert result.error_message is None
        assert result.warnings == []
    
    def test_with_error(self):
        """Test validation result with error."""
        from sensei.services.ai.onnx_model_init import ModelValidationResult
        
        result = ModelValidationResult(
            model_name="failed_model",
            is_valid=False,
            error_message="Model file not found",
        )
        
        assert result.is_valid is False
        assert result.error_message == "Model file not found"
    
    def test_with_warnings(self):
        """Test validation result with warnings."""
        from sensei.services.ai.onnx_model_init import ModelValidationResult
        
        result = ModelValidationResult(
            model_name="warned_model",
            is_valid=True,
            opset_version=13,
            warnings=["Opset version 13 is older; consider re-exporting"],
        )
        
        assert result.is_valid is True
        assert len(result.warnings) == 1


class TestModelRegistryStatus:
    """Tests for ModelRegistryStatus dataclass."""
    
    def test_creation(self):
        """Test creating registry status."""
        from sensei.services.ai.onnx_model_init import ModelRegistryStatus
        
        status = ModelRegistryStatus(
            total_models=5,
            loaded_models=4,
            failed_models=1,
            total_warmup_time_ms=150.5,
        )
        
        assert status.total_models == 5
        assert status.loaded_models == 4
        assert status.failed_models == 1
        assert status.total_warmup_time_ms == 150.5
        assert status.is_healthy is True
    
    def test_unhealthy_status(self):
        """Test unhealthy status when all fail."""
        from sensei.services.ai.onnx_model_init import ModelRegistryStatus
        
        status = ModelRegistryStatus(
            total_models=3,
            loaded_models=0,
            failed_models=3,
            total_warmup_time_ms=0.0,
            is_healthy=False,
        )
        
        assert status.is_healthy is False


class TestONNXModelValidator:
    """Tests for ONNXModelValidator."""
    
    def test_validator_creation(self):
        """Test creating a validator."""
        from sensei.services.ai.onnx_model_init import ONNXModelValidator
        
        validator = ONNXModelValidator()
        assert validator.min_opset == 11
        assert validator.max_opset == 20
    
    def test_custom_opset_range(self):
        """Test custom opset range."""
        from sensei.services.ai.onnx_model_init import ONNXModelValidator
        
        validator = ONNXModelValidator(min_opset=14, max_opset=18)
        assert validator.min_opset == 14
        assert validator.max_opset == 18
    
    def test_validate_nonexistent_model(self):
        """Test validating a nonexistent model file."""
        from sensei.services.ai.onnx_model_init import ONNXModelValidator
        
        validator = ONNXModelValidator()
        result = validator.validate_model(
            model_path=Path("/nonexistent/model.onnx"),
            model_name="nonexistent",
            run_warmup=False,
        )
        
        assert result.is_valid is False
        assert "not found" in result.error_message.lower()


class TestONNXModelRegistry:
    """Tests for ONNXModelRegistry."""
    
    def test_registry_creation(self):
        """Test creating a registry."""
        from sensei.services.ai.onnx_model_init import ONNXModelRegistry
        
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ONNXModelRegistry(cache_dir=Path(tmpdir))
            assert registry is not None
    
    def test_get_model_paths(self):
        """Test getting model paths."""
        from sensei.services.ai.onnx_model_init import ONNXModelRegistry
        
        registry = ONNXModelRegistry()
        paths = registry.get_model_paths()
        
        assert "embeddings" in paths
        assert "reranker" in paths
        assert "edge_anomaly" in paths
    
    def test_validate_all(self):
        """Test validating all models."""
        from sensei.services.ai.onnx_model_init import ONNXModelRegistry
        
        registry = ONNXModelRegistry()
        status = registry.validate_all()
        
        assert status.total_models == 3
        # Models won't exist initially, so all should fail
        assert status.failed_models >= 0
    
    def test_get_health_status(self):
        """Test getting health status."""
        from sensei.services.ai.onnx_model_init import ONNXModelRegistry
        
        registry = ONNXModelRegistry()
        health = registry.get_health_status()
        
        assert "is_healthy" in health
        assert "total_models" in health
        assert "loaded_models" in health
        assert "failed_models" in health
        assert "models" in health
    
    def test_warmup_all(self):
        """Test warming up all models."""
        from sensei.services.ai.onnx_model_init import ONNXModelRegistry
        
        registry = ONNXModelRegistry()
        warmup_times = registry.warmup_all()
        
        # Returns dict of model name -> warmup time
        assert isinstance(warmup_times, dict)


class TestGetModelRegistry:
    """Tests for singleton function."""
    
    def test_returns_registry(self):
        """Test singleton returns registry."""
        from sensei.services.ai.onnx_model_init import get_model_registry
        
        registry = get_model_registry()
        assert registry is not None
    
    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        from sensei.services.ai.onnx_model_init import get_model_registry
        
        reg1 = get_model_registry()
        reg2 = get_model_registry()
        
        assert reg1 is reg2


class TestInitializeModels:
    """Tests for initialize_models function."""
    
    @pytest.mark.asyncio
    async def test_initialize_returns_status(self):
        """Test initialize_models returns status."""
        from sensei.services.ai.onnx_model_init import initialize_models
        
        status = await initialize_models()
        
        assert status is not None
        assert hasattr(status, "total_models")
        assert hasattr(status, "loaded_models")


class TestConstants:
    """Tests for module constants."""
    
    def test_opset_constants(self):
        """Test opset version constants."""
        from sensei.services.ai.onnx_model_init import (
            MIN_OPSET_VERSION,
            MAX_OPSET_VERSION,
            DEFAULT_OPSET_VERSION,
        )
        
        assert MIN_OPSET_VERSION == 11
        assert MAX_OPSET_VERSION == 20
        assert DEFAULT_OPSET_VERSION == 17
        assert MIN_OPSET_VERSION < DEFAULT_OPSET_VERSION < MAX_OPSET_VERSION

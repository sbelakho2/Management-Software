"""
ONNX Model Initialization and Validation.

This module provides:
- Model warm-up on application startup
- Opset version validation
- Model health checks
- Pre-flight validation for all ONNX models

Use this module to ensure all ONNX models are ready before
accepting requests, reducing cold-start latency.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Minimum supported ONNX opset version
MIN_OPSET_VERSION = 11
# Maximum supported ONNX opset version  
MAX_OPSET_VERSION = 20
# Default opset version for exports
DEFAULT_OPSET_VERSION = 17


@dataclass
class ModelValidationResult:
    """Result of model validation."""
    model_name: str
    is_valid: bool
    opset_version: Optional[int] = None
    warmup_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ModelRegistryStatus:
    """Status of all registered models."""
    total_models: int
    loaded_models: int
    failed_models: int
    total_warmup_time_ms: float
    validation_results: List[ModelValidationResult] = field(default_factory=list)
    is_healthy: bool = True


class ONNXModelValidator:
    """
    Validates ONNX models for production readiness.
    
    Checks:
    - Opset version compatibility
    - Input/output schema
    - Warm-up inference
    - Memory requirements
    """
    
    def __init__(
        self,
        min_opset: int = MIN_OPSET_VERSION,
        max_opset: int = MAX_OPSET_VERSION,
    ):
        self.min_opset = min_opset
        self.max_opset = max_opset
    
    def validate_opset(self, model_path: Path) -> tuple[bool, Optional[int], Optional[str]]:
        """
        Validate the opset version of an ONNX model.
        
        Returns:
            Tuple of (is_valid, opset_version, error_message)
        """
        try:
            import onnx
            
            model = onnx.load(model_path.as_posix())
            opset_imports = model.opset_import
            
            # Get the main opset version
            opset_version = None
            for opset in opset_imports:
                if opset.domain == "" or opset.domain == "ai.onnx":
                    opset_version = opset.version
                    break
            
            if opset_version is None:
                return False, None, "Could not determine opset version"
            
            if opset_version < self.min_opset:
                return False, opset_version, f"Opset version {opset_version} is below minimum {self.min_opset}"
            
            if opset_version > self.max_opset:
                return False, opset_version, f"Opset version {opset_version} is above maximum {self.max_opset}"
            
            return True, opset_version, None
            
        except ImportError:
            return True, None, None  # Skip validation if onnx not installed
        except Exception as e:
            return False, None, f"Failed to validate opset: {e}"
    
    def validate_model(
        self,
        model_path: Path,
        model_name: str,
        run_warmup: bool = True,
    ) -> ModelValidationResult:
        """
        Perform full validation of an ONNX model.
        
        Args:
            model_path: Path to the ONNX model file
            model_name: Name for the model (for logging)
            run_warmup: Whether to run warm-up inference
            
        Returns:
            ModelValidationResult with validation status
        """
        result = ModelValidationResult(model_name=model_name, is_valid=True)
        
        # Check file exists
        if not model_path.exists():
            result.is_valid = False
            result.error_message = f"Model file not found: {model_path}"
            return result
        
        # Validate opset version
        opset_valid, opset_version, opset_error = self.validate_opset(model_path)
        result.opset_version = opset_version
        
        if not opset_valid:
            result.is_valid = False
            result.error_message = opset_error
            return result
        
        if opset_version and opset_version < 14:
            result.warnings.append(
                f"Opset version {opset_version} is older; consider re-exporting with opset 17"
            )
        
        # Try loading with ONNX Runtime
        try:
            import onnxruntime as ort
            
            session = ort.InferenceSession(
                model_path.as_posix(),
                providers=["CPUExecutionProvider"],
            )
            
            # Get input/output info
            inputs = session.get_inputs()
            outputs = session.get_outputs()
            
            logger.debug(
                f"Model {model_name}: {len(inputs)} inputs, {len(outputs)} outputs"
            )
            
            # Run warm-up if requested
            if run_warmup:
                warmup_time = self._run_warmup(session, inputs)
                result.warmup_time_ms = warmup_time
                
                if warmup_time > 1000:
                    result.warnings.append(
                        f"Slow warm-up time: {warmup_time:.1f}ms"
                    )
            
        except ImportError:
            result.warnings.append("ONNX Runtime not available, skipped loading test")
        except Exception as e:
            result.is_valid = False
            result.error_message = f"Failed to load model: {e}"
        
        return result
    
    def _run_warmup(
        self,
        session: Any,  # ort.InferenceSession
        inputs: List[Any],
    ) -> float:
        """Run warm-up inference and return time in milliseconds."""
        import numpy as np
        
        # Create dummy inputs
        feed_dict = {}
        for inp in inputs:
            shape = list(inp.shape)
            # Replace dynamic dimensions with reasonable values
            for i, dim in enumerate(shape):
                if isinstance(dim, str) or dim is None or dim < 0:
                    shape[i] = 1 if i == 0 else 64  # batch=1, others=64
            
            dtype = np.float32
            if inp.type == "tensor(int64)":
                dtype = np.int64
            elif inp.type == "tensor(int32)":
                dtype = np.int32
            
            feed_dict[inp.name] = np.zeros(shape, dtype=dtype)
        
        # Run warm-up
        start = time.perf_counter()
        try:
            _ = session.run(None, feed_dict)
        except Exception as e:
            logger.warning(f"Warm-up inference failed: {e}")
        end = time.perf_counter()
        
        return (end - start) * 1000


class ONNXModelRegistry:
    """
    Registry for managing and initializing all ONNX models.
    
    Provides:
    - Centralized model loading
    - Batch warm-up on startup
    - Health status monitoring
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        auto_warmup: bool = True,
    ):
        self.cache_dir = cache_dir or Path(
            os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx")
        )
        self.auto_warmup = auto_warmup
        self.validator = ONNXModelValidator()
        self._models: Dict[str, Any] = {}
        self._validation_results: Dict[str, ModelValidationResult] = {}
    
    def get_model_paths(self) -> Dict[str, Path]:
        """Get all expected model paths."""
        paths = {}
        
        # Text embeddings
        embedding_model = os.getenv(
            "SENSEI_ONNX_EMBEDDING_MODEL",
            "sentence-transformers__all-MiniLM-L6-v2"
        )
        paths["embeddings"] = self.cache_dir / f"{embedding_model}.int8.onnx"
        
        # Cross-encoder reranker
        reranker_model = os.getenv(
            "SENSEI_ONNX_RERANKER_MODEL",
            "cross-encoder__ms-marco-MiniLM-L-6-v2"
        ).replace("/", "__")
        paths["reranker"] = self.cache_dir / f"{reranker_model}_reranker.int8.onnx"
        
        # Edge anomaly detector
        paths["edge_anomaly"] = self.cache_dir / "edge_anomaly_detector.int8.onnx"
        
        return paths
    
    def validate_all(self) -> ModelRegistryStatus:
        """Validate all registered models."""
        paths = self.get_model_paths()
        
        status = ModelRegistryStatus(
            total_models=len(paths),
            loaded_models=0,
            failed_models=0,
            total_warmup_time_ms=0.0,
        )
        
        for name, path in paths.items():
            result = self.validator.validate_model(
                model_path=path,
                model_name=name,
                run_warmup=self.auto_warmup,
            )
            
            self._validation_results[name] = result
            status.validation_results.append(result)
            
            if result.is_valid:
                status.loaded_models += 1
                if result.warmup_time_ms:
                    status.total_warmup_time_ms += result.warmup_time_ms
            else:
                status.failed_models += 1
                logger.warning(
                    f"Model validation failed: {name} - {result.error_message}"
                )
        
        status.is_healthy = status.failed_models == 0
        
        return status
    
    def warmup_all(self) -> Dict[str, float]:
        """
        Warm up all loaded models.
        
        Returns:
            Dict mapping model name to warm-up time in milliseconds
        """
        warmup_times = {}
        paths = self.get_model_paths()
        
        for name, path in paths.items():
            if not path.exists():
                continue
            
            result = self.validator.validate_model(
                model_path=path,
                model_name=name,
                run_warmup=True,
            )
            
            if result.warmup_time_ms:
                warmup_times[name] = result.warmup_time_ms
        
        total_time = sum(warmup_times.values())
        logger.info(
            f"ONNX model warm-up complete: {len(warmup_times)} models, "
            f"{total_time:.1f}ms total"
        )
        
        return warmup_times
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all models."""
        status = self.validate_all()
        
        return {
            "is_healthy": status.is_healthy,
            "total_models": status.total_models,
            "loaded_models": status.loaded_models,
            "failed_models": status.failed_models,
            "total_warmup_time_ms": status.total_warmup_time_ms,
            "models": {
                r.model_name: {
                    "is_valid": r.is_valid,
                    "opset_version": r.opset_version,
                    "warmup_time_ms": r.warmup_time_ms,
                    "error": r.error_message,
                    "warnings": r.warnings,
                }
                for r in status.validation_results
            }
        }


# Singleton instance
_model_registry: Optional[ONNXModelRegistry] = None


def get_model_registry() -> ONNXModelRegistry:
    """Get the singleton model registry instance."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ONNXModelRegistry()
    return _model_registry


async def initialize_models() -> ModelRegistryStatus:
    """
    Initialize and warm up all ONNX models on application startup.
    
    Call this during application startup to:
    1. Export any missing models to ONNX format
    2. Validate all model files
    3. Warm up for consistent latency
    
    Returns:
        ModelRegistryStatus with initialization results
    """
    logger.info("Initializing ONNX models...")
    
    registry = get_model_registry()
    
    # Trigger model exports by importing the modules
    try:
        from sensei.services.ai.onnx_text_embeddings import get_onnx_embedder
        embedder = get_onnx_embedder()
        logger.debug(f"Embeddings ready: {embedder.is_loaded()}")
    except Exception as e:
        logger.warning(f"Could not initialize embeddings: {e}")
    
    try:
        from sensei.services.ai.onnx_cross_encoder import get_cross_encoder
        cross_encoder = get_cross_encoder()
        logger.debug(f"Cross-encoder ready: {cross_encoder.is_loaded()}")
    except Exception as e:
        logger.warning(f"Could not initialize cross-encoder: {e}")
    
    try:
        from sensei.services.core.onnx_edge_inference import get_onnx_edge_inference
        edge_model = get_onnx_edge_inference()
        logger.debug(f"Edge model ready: {edge_model.is_ready()}")
    except Exception as e:
        logger.warning(f"Could not initialize edge model: {e}")
    
    # Validate all models
    status = registry.validate_all()
    
    logger.info(
        f"ONNX initialization complete: "
        f"{status.loaded_models}/{status.total_models} models ready, "
        f"{status.total_warmup_time_ms:.1f}ms warm-up time"
    )
    
    return status

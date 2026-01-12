"""
Local-First Infrastructure with ONNX Runtime Optimization

This module provides infrastructure for local AI execution:
- On-device execution with ONNX Runtime
- Model optimization (INT8/Float16 quantization)
- Memory management and throttling
- Fallback strategies for resilience
- Circuit breaker pattern for model loading
"""

from __future__ import annotations

import gc
import logging
import os
import threading
import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Configuration
# =============================================================================

class ModelPrecision(Enum):
    """Model precision options for ONNX optimization."""
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"
    DYNAMIC_QUANTIZED = "dynamic_quantized"


class ModelSize(Enum):
    """Model size variants."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class ExecutionProvider(Enum):
    """ONNX Runtime execution providers."""
    CPU = "CPUExecutionProvider"
    CUDA = "CUDAExecutionProvider"
    TENSORRT = "TensorRTExecutionProvider"
    DIRECTML = "DMLExecutionProvider"
    COREML = "CoreMLExecutionProvider"


@dataclass
class ModelConfig:
    """Configuration for an ONNX model."""
    model_path: Path
    model_name: str
    precision: ModelPrecision = ModelPrecision.FLOAT32
    size_variant: ModelSize = ModelSize.MEDIUM
    memory_mb: int = 512
    warmup_required: bool = True
    input_names: List[str] = field(default_factory=lambda: ["input"])
    output_names: List[str] = field(default_factory=lambda: ["output"])
    dynamic_axes: Optional[Dict[str, Dict[int, str]]] = None


@dataclass
class InferenceResult:
    """Result from model inference."""
    outputs: Dict[str, np.ndarray]
    latency_ms: float
    model_name: str
    used_fallback: bool = False
    fallback_reason: Optional[str] = None


@dataclass
class SystemResources:
    """Current system resource availability."""
    available_ram_mb: float
    total_ram_mb: float
    cpu_count: int
    cpu_usage_percent: float
    available_threads: int


# =============================================================================
# Memory Management
# =============================================================================

class MemoryManager:
    """
    Predictive memory throttling for ONNX models.
    
    Pre-checks available RAM before loading large models and
    suggests appropriate model variants.
    """
    
    MINIMUM_FREE_RAM_MB = 512  # Keep at least 512MB free
    SMALL_MODEL_THRESHOLD_MB = 2048  # Use small models if <2GB free
    
    def __init__(self):
        self._lock = threading.Lock()
    
    def get_system_resources(self) -> SystemResources:
        """Get current system resource availability."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            cpu_count = os.cpu_count() or 1
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return SystemResources(
                available_ram_mb=memory.available / (1024 * 1024),
                total_ram_mb=memory.total / (1024 * 1024),
                cpu_count=cpu_count,
                cpu_usage_percent=cpu_percent,
                available_threads=max(1, cpu_count - int(cpu_count * cpu_percent / 100)),
            )
        except ImportError:
            # Fallback without psutil
            cpu_count = os.cpu_count() or 1
            return SystemResources(
                available_ram_mb=4096.0,  # Assume 4GB available
                total_ram_mb=8192.0,
                cpu_count=cpu_count,
                cpu_usage_percent=50.0,
                available_threads=max(1, cpu_count // 2),
            )
    
    def check_memory_for_model(
        self,
        required_mb: float,
        safety_factor: float = 1.2,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if there's enough memory to load a model.
        
        Args:
            required_mb: Required memory in MB
            safety_factor: Multiply required by this for safety margin
            
        Returns:
            Tuple of (can_load, reason_if_not)
        """
        with self._lock:
            resources = self.get_system_resources()
            required_with_safety = required_mb * safety_factor
            available_after = resources.available_ram_mb - required_with_safety
            
            if available_after < self.MINIMUM_FREE_RAM_MB:
                return False, (
                    f"Insufficient memory: need {required_with_safety:.0f}MB, "
                    f"have {resources.available_ram_mb:.0f}MB available, "
                    f"would leave {available_after:.0f}MB (min: {self.MINIMUM_FREE_RAM_MB}MB)"
                )
            
            return True, None
    
    def suggest_model_variant(self, preferred: ModelSize) -> ModelSize:
        """
        Suggest appropriate model variant based on available memory.
        
        Args:
            preferred: The preferred model size
            
        Returns:
            Suggested model size (may be smaller than preferred)
        """
        resources = self.get_system_resources()
        
        if resources.available_ram_mb < self.SMALL_MODEL_THRESHOLD_MB:
            return ModelSize.SMALL
        
        if resources.available_ram_mb < self.SMALL_MODEL_THRESHOLD_MB * 2:
            if preferred == ModelSize.LARGE:
                return ModelSize.MEDIUM
        
        return preferred
    
    def get_optimal_thread_count(self) -> int:
        """
        Get optimal thread count for inference based on system load.
        
        Returns:
            Recommended number of threads
        """
        resources = self.get_system_resources()
        
        # Use available threads, but leave some for system
        optimal = max(1, resources.available_threads - 1)
        
        # Cap at reasonable maximum
        return min(optimal, 8)
    
    def cleanup(self) -> None:
        """Force garbage collection to free memory."""
        gc.collect()


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for model loading to prevent system hang on OOM.
    
    States:
    - CLOSED: Normal operation, allow model loading
    - OPEN: Too many failures, reject model loading attempts
    - HALF_OPEN: Testing if system has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_s: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        with self._lock:
            self._check_recovery()
            return self._state
    
    def _check_recovery(self) -> None:
        """Check if circuit should transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout_s:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
    
    def can_proceed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if an operation can proceed.
        
        Returns:
            Tuple of (can_proceed, reason_if_not)
        """
        with self._lock:
            self._check_recovery()
            
            if self._state == CircuitState.CLOSED:
                return True, None
            
            if self._state == CircuitState.OPEN:
                wait_time = self.recovery_timeout_s
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    wait_time = max(0, self.recovery_timeout_s - elapsed)
                return False, f"Circuit OPEN, retry in {wait_time:.1f}s"
            
            # HALF_OPEN
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True, None
            
            return False, "Circuit HALF_OPEN, max test calls reached"
    
    def record_success(self) -> None:
        """Record a successful operation."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker recovered, transitioning to CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
    
    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker test failed, returning to OPEN")
                self._state = CircuitState.OPEN
                return
            
            if self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker opening after {self._failure_count} failures: {error}"
                )
                self._state = CircuitState.OPEN
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0


# =============================================================================
# Fallback Strategies
# =============================================================================

class FallbackStrategy(ABC):
    """Base class for fallback strategies when AI models fail."""
    
    @abstractmethod
    def can_handle(self, input_type: str) -> bool:
        """Check if this fallback can handle the input type."""
        pass
    
    @abstractmethod
    def execute(self, input_data: Any, context: Optional[Dict] = None) -> Any:
        """Execute the fallback strategy."""
        pass


class RegexFallback(FallbackStrategy):
    """Rule-based fallback using regex patterns."""
    
    def __init__(self):
        # Common patterns for different input types
        self._patterns: Dict[str, List[Tuple[re.Pattern, Callable]]] = {
            "email_extraction": [
                (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 
                 lambda m: {"email": m.group()}),
            ],
            "phone_extraction": [
                (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
                 lambda m: {"phone": m.group()}),
            ],
            "date_extraction": [
                (re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
                 lambda m: {"date": m.group()}),
                (re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
                 lambda m: {"date": m.group()}),
            ],
            "number_extraction": [
                (re.compile(r'\$?\d+(?:,\d{3})*(?:\.\d{2})?'),
                 lambda m: {"amount": m.group()}),
            ],
            "part_number": [
                (re.compile(r'\b[A-Z]{2,4}-\d{4,8}(?:-[A-Z0-9]+)?\b'),
                 lambda m: {"part_number": m.group()}),
            ],
        }
    
    def can_handle(self, input_type: str) -> bool:
        return input_type in self._patterns
    
    def execute(self, input_data: Any, context: Optional[Dict] = None) -> Any:
        input_type = context.get("type", "") if context else ""
        text = str(input_data)
        
        results = []
        patterns = self._patterns.get(input_type, [])
        
        for pattern, extractor in patterns:
            for match in pattern.finditer(text):
                results.append(extractor(match))
        
        return results


class HeuristicFallback(FallbackStrategy):
    """Heuristic-based fallback for structured data extraction."""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {
            "text_classification": self._classify_text,
            "sentiment": self._analyze_sentiment,
            "language_detection": self._detect_language,
            "entity_extraction": self._extract_entities,
        }
    
    def can_handle(self, input_type: str) -> bool:
        return input_type in self._handlers
    
    def execute(self, input_data: Any, context: Optional[Dict] = None) -> Any:
        input_type = context.get("type", "") if context else ""
        handler = self._handlers.get(input_type)
        if handler:
            return handler(input_data, context)
        return None
    
    def _classify_text(self, text: str, context: Optional[Dict] = None) -> Dict[str, float]:
        """Simple keyword-based text classification."""
        text_lower = text.lower()
        
        categories = {
            "urgent": ["urgent", "asap", "immediately", "critical", "emergency"],
            "question": ["?", "what", "when", "where", "how", "why", "who"],
            "request": ["please", "could you", "can you", "would you", "need"],
            "complaint": ["issue", "problem", "wrong", "error", "broken", "fail"],
            "positive": ["thank", "great", "good", "excellent", "appreciate"],
        }
        
        scores = {}
        for category, keywords in categories.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = min(1.0, count * 0.25)
        
        return scores
    
    def _analyze_sentiment(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Simple sentiment analysis based on word lists."""
        text_lower = text.lower()
        
        positive_words = {
            "good", "great", "excellent", "wonderful", "amazing",
            "fantastic", "love", "happy", "pleased", "satisfied",
            "thank", "appreciate", "helpful", "perfect", "best",
        }
        
        negative_words = {
            "bad", "terrible", "awful", "horrible", "hate",
            "disappointed", "angry", "frustrated", "annoyed", "worst",
            "problem", "issue", "error", "fail", "wrong",
        }
        
        words = set(text_lower.split())
        positive_count = len(words & positive_words)
        negative_count = len(words & negative_words)
        
        total = positive_count + negative_count
        if total == 0:
            sentiment = "neutral"
            confidence = 0.5
        elif positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.95, 0.5 + (positive_count - negative_count) * 0.1)
        else:
            sentiment = "negative"
            confidence = min(0.95, 0.5 + (negative_count - positive_count) * 0.1)
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_count": positive_count,
            "negative_count": negative_count,
        }
    
    def _detect_language(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Simple language detection based on character patterns."""
        # Count character types
        ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
        total_letters = sum(1 for c in text if c.isalpha())
        
        if total_letters == 0:
            return {"language": "unknown", "confidence": 0.0}
        
        ascii_ratio = ascii_letters / total_letters
        
        # Check for common language patterns
        if ascii_ratio > 0.9:
            # English detection (common words)
            english_indicators = ["the", "and", "is", "are", "was", "were", "be", "to", "of"]
            text_lower = text.lower()
            english_count = sum(1 for word in english_indicators if word in text_lower.split())
            
            if english_count >= 2:
                return {"language": "en", "confidence": 0.8}
            return {"language": "en", "confidence": 0.5}
        
        return {"language": "unknown", "confidence": 0.3}
    
    def _extract_entities(self, text: str, context: Optional[Dict] = None) -> List[Dict]:
        """Simple entity extraction using patterns."""
        entities = []
        
        # Proper nouns (capitalized words not at sentence start)
        words = text.split()
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 1:
                entities.append({
                    "text": word.strip(".,!?"),
                    "type": "PROPER_NOUN",
                    "confidence": 0.6,
                })
        
        # Numbers/quantities
        number_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:units?|pcs?|pieces?|items?|kg|lbs?)?\b', re.I)
        for match in number_pattern.finditer(text):
            entities.append({
                "text": match.group(),
                "type": "QUANTITY",
                "confidence": 0.8,
            })
        
        return entities


class FallbackManager:
    """Manages fallback strategies and their execution."""
    
    def __init__(self):
        self._strategies: List[FallbackStrategy] = [
            RegexFallback(),
            HeuristicFallback(),
        ]
    
    def add_strategy(self, strategy: FallbackStrategy) -> None:
        """Add a fallback strategy."""
        self._strategies.append(strategy)
    
    def execute(
        self,
        input_data: Any,
        input_type: str,
        context: Optional[Dict] = None,
    ) -> Tuple[Any, str]:
        """
        Execute fallback strategies.
        
        Args:
            input_data: The input to process
            input_type: Type of input/operation
            context: Additional context
            
        Returns:
            Tuple of (result, strategy_name)
        """
        ctx = {"type": input_type, **(context or {})}
        
        for strategy in self._strategies:
            if strategy.can_handle(input_type):
                try:
                    result = strategy.execute(input_data, ctx)
                    return result, strategy.__class__.__name__
                except Exception as e:
                    logger.warning(f"Fallback {strategy.__class__.__name__} failed: {e}")
                    continue
        
        return None, "none"


# =============================================================================
# ONNX Model Manager
# =============================================================================

class ONNXModelSession:
    """Wrapper for ONNX Runtime inference session."""
    
    def __init__(
        self,
        config: ModelConfig,
        session: Any,  # ort.InferenceSession
        warmed_up: bool = False,
    ):
        self.config = config
        self.session = session
        self.warmed_up = warmed_up
        self.load_time = time.time()
        self.inference_count = 0
        self.total_inference_time_ms = 0.0
    
    @property
    def average_inference_time_ms(self) -> float:
        """Average inference time in milliseconds."""
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_time_ms / self.inference_count
    
    def warmup(self, dummy_input: Optional[Dict[str, np.ndarray]] = None) -> float:
        """
        Warm up the model with dummy inference.
        
        Args:
            dummy_input: Optional custom dummy input
            
        Returns:
            Warmup time in milliseconds
        """
        if self.warmed_up:
            return 0.0
        
        start = time.perf_counter()
        
        if dummy_input is None:
            # Create dummy input based on session inputs
            dummy_input = {}
            for inp in self.session.get_inputs():
                shape = inp.shape
                # Replace dynamic dims with small values
                resolved_shape = tuple(
                    1 if isinstance(dim, str) else dim 
                    for dim in shape
                )
                dtype = np.float32 if "float" in inp.type else np.int64
                dummy_input[inp.name] = np.zeros(resolved_shape, dtype=dtype)
        
        # Run dummy inference
        try:
            _ = self.session.run(None, dummy_input)
        except Exception as e:
            logger.warning(f"Warmup inference failed: {e}")
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.warmed_up = True
        logger.info(f"Model {self.config.model_name} warmed up in {elapsed_ms:.2f}ms")
        
        return elapsed_ms


class ONNXModelManager:
    """
    Manages ONNX model lifecycle including loading, inference, and cleanup.
    
    Features:
    - Dynamic thread configuration
    - Memory-aware model loading
    - Circuit breaker for fault tolerance
    - Model warmup for consistent latency
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        max_models: int = 5,
    ):
        self.model_dir = model_dir or Path("models")
        self.max_models = max_models
        
        self._models: Dict[str, ONNXModelSession] = {}
        self._lock = threading.Lock()
        self._memory_manager = MemoryManager()
        self._circuit_breaker = CircuitBreaker()
        self._fallback_manager = FallbackManager()
        
        # Configure ONNX Runtime threads
        self._configure_threading()
    
    def _configure_threading(self) -> None:
        """Configure ONNX Runtime threading based on system resources."""
        optimal_threads = self._memory_manager.get_optimal_thread_count()
        
        # Set environment variables for OpenMP/MKL
        os.environ["OMP_NUM_THREADS"] = str(optimal_threads)
        os.environ["MKL_NUM_THREADS"] = str(optimal_threads)
        
        logger.info(f"Configured ONNX Runtime for {optimal_threads} threads")
    
    def _get_session_options(self) -> Any:
        """Get ONNX Runtime session options."""
        try:
            import onnxruntime as ort
            
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = self._memory_manager.get_optimal_thread_count()
            opts.intra_op_num_threads = self._memory_manager.get_optimal_thread_count()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            return opts
        except ImportError:
            return None
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used model if at capacity."""
        with self._lock:
            if len(self._models) >= self.max_models:
                # Find LRU model
                oldest_name = min(
                    self._models.keys(),
                    key=lambda k: self._models[k].load_time
                )
                self._unload_model(oldest_name)
    
    def _unload_model(self, model_name: str) -> None:
        """Unload a model and free memory."""
        if model_name in self._models:
            del self._models[model_name]
            self._memory_manager.cleanup()
            logger.info(f"Unloaded model: {model_name}")
    
    def load_model(
        self,
        config: ModelConfig,
        force: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Load an ONNX model with memory checks and circuit breaker.
        
        Args:
            config: Model configuration
            force: Force load even if memory is low
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check circuit breaker
        can_proceed, reason = self._circuit_breaker.can_proceed()
        if not can_proceed:
            return False, reason
        
        # Check if already loaded
        if config.model_name in self._models:
            return True, None
        
        # Check memory
        if not force:
            can_load, reason = self._memory_manager.check_memory_for_model(
                config.memory_mb
            )
            if not can_load:
                # Try suggesting smaller variant
                suggested = self._memory_manager.suggest_model_variant(
                    config.size_variant
                )
                if suggested != config.size_variant:
                    return False, (
                        f"{reason}. Consider using {suggested.value} variant."
                    )
                return False, reason
        
        # Evict if needed
        self._evict_if_needed()
        
        # Try to load model
        try:
            import onnxruntime as ort
            
            model_path = config.model_path
            if not model_path.is_absolute():
                model_path = self.model_dir / model_path
            
            if not model_path.exists():
                return False, f"Model file not found: {model_path}"
            
            opts = self._get_session_options()
            session = ort.InferenceSession(
                str(model_path),
                sess_options=opts,
                providers=[ExecutionProvider.CPU.value],
            )
            
            model_session = ONNXModelSession(config, session)
            
            # Warmup if required
            if config.warmup_required:
                model_session.warmup()
            
            with self._lock:
                self._models[config.model_name] = model_session
            
            self._circuit_breaker.record_success()
            logger.info(f"Loaded model: {config.model_name}")
            return True, None
            
        except ImportError:
            error_msg = "ONNX Runtime not installed"
            self._circuit_breaker.record_failure()
            return False, error_msg
            
        except Exception as e:
            self._circuit_breaker.record_failure(e)
            return False, f"Failed to load model: {str(e)}"
    
    def infer(
        self,
        model_name: str,
        inputs: Dict[str, np.ndarray],
        fallback_type: Optional[str] = None,
        fallback_input: Optional[Any] = None,
    ) -> InferenceResult:
        """
        Run inference on a model with fallback support.
        
        Args:
            model_name: Name of the model to use
            inputs: Input tensors as dict
            fallback_type: Type for fallback if inference fails
            fallback_input: Input data for fallback
            
        Returns:
            InferenceResult with outputs or fallback results
        """
        # Check if model is loaded
        if model_name not in self._models:
            # Try fallback
            if fallback_type and fallback_input:
                result, strategy = self._fallback_manager.execute(
                    fallback_input, fallback_type
                )
                return InferenceResult(
                    outputs={"fallback": np.array([result])},
                    latency_ms=0.0,
                    model_name=model_name,
                    used_fallback=True,
                    fallback_reason=f"Model not loaded, used {strategy}",
                )
            raise ValueError(f"Model {model_name} not loaded")
        
        model_session = self._models[model_name]
        
        try:
            start = time.perf_counter()
            outputs = model_session.session.run(None, inputs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            # Update stats
            model_session.inference_count += 1
            model_session.total_inference_time_ms += elapsed_ms
            
            # Build output dict
            output_names = [o.name for o in model_session.session.get_outputs()]
            output_dict = dict(zip(output_names, outputs))
            
            return InferenceResult(
                outputs=output_dict,
                latency_ms=elapsed_ms,
                model_name=model_name,
            )
            
        except Exception as e:
            logger.error(f"Inference failed for {model_name}: {e}")
            
            # Try fallback
            if fallback_type and fallback_input:
                result, strategy = self._fallback_manager.execute(
                    fallback_input, fallback_type
                )
                return InferenceResult(
                    outputs={"fallback": np.array([result])},
                    latency_ms=0.0,
                    model_name=model_name,
                    used_fallback=True,
                    fallback_reason=f"Inference error, used {strategy}",
                )
            raise
    
    def get_model_stats(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a loaded model."""
        if model_name not in self._models:
            return None
        
        session = self._models[model_name]
        return {
            "model_name": model_name,
            "load_time": session.load_time,
            "warmed_up": session.warmed_up,
            "inference_count": session.inference_count,
            "average_inference_time_ms": session.average_inference_time_ms,
            "precision": session.config.precision.value,
            "size_variant": session.config.size_variant.value,
        }
    
    def list_models(self) -> List[str]:
        """List loaded model names."""
        return list(self._models.keys())
    
    def unload_all(self) -> None:
        """Unload all models."""
        with self._lock:
            self._models.clear()
            self._memory_manager.cleanup()
        logger.info("Unloaded all models")
    
    @property
    def circuit_breaker_state(self) -> CircuitState:
        """Current circuit breaker state."""
        return self._circuit_breaker.state
    
    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker."""
        self._circuit_breaker.reset()


# =============================================================================
# ONNX Model Optimization
# =============================================================================

class ONNXOptimizer:
    """
    Utilities for ONNX model optimization including quantization.
    """
    
    @staticmethod
    def quantize_model(
        input_path: Path,
        output_path: Path,
        precision: ModelPrecision = ModelPrecision.INT8,
        per_channel: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Quantize an ONNX model to reduce size and improve inference speed.
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path for output quantized model
            precision: Target precision
            per_channel: Use per-channel quantization (more accurate)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType
            
            if precision == ModelPrecision.INT8:
                quant_type = QuantType.QInt8
            elif precision == ModelPrecision.DYNAMIC_QUANTIZED:
                quant_type = QuantType.QUInt8
            else:
                return False, f"Unsupported precision for quantization: {precision}"
            
            quantize_dynamic(
                str(input_path),
                str(output_path),
                per_channel=per_channel,
                weight_type=quant_type,
            )
            
            logger.info(f"Quantized model saved to {output_path}")
            return True, None
            
        except ImportError:
            return False, "onnxruntime quantization not available"
        except Exception as e:
            return False, f"Quantization failed: {str(e)}"
    
    @staticmethod
    def optimize_graph(
        input_path: Path,
        output_path: Path,
        optimization_level: str = "all",
    ) -> Tuple[bool, Optional[str]]:
        """
        Apply graph optimizations to an ONNX model.
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path for output optimized model
            optimization_level: Level of optimization (basic, extended, all)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            import onnxruntime as ort
            
            opts = ort.SessionOptions()
            
            if optimization_level == "basic":
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            elif optimization_level == "extended":
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
            else:
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            opts.optimized_model_filepath = str(output_path)
            
            # Load session (which triggers optimization)
            _ = ort.InferenceSession(
                str(input_path),
                sess_options=opts,
                providers=[ExecutionProvider.CPU.value],
            )
            
            logger.info(f"Optimized model saved to {output_path}")
            return True, None
            
        except ImportError:
            return False, "onnxruntime not available"
        except Exception as e:
            return False, f"Optimization failed: {str(e)}"
    
    @staticmethod
    def convert_to_float16(
        input_path: Path,
        output_path: Path,
    ) -> Tuple[bool, Optional[str]]:
        """
        Convert model to Float16 precision.
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path for output Float16 model
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            import onnx
            from onnxruntime.transformers import float16
            
            model = onnx.load(str(input_path))
            model_fp16 = float16.convert_float_to_float16(model)
            onnx.save(model_fp16, str(output_path))
            
            logger.info(f"Float16 model saved to {output_path}")
            return True, None
            
        except ImportError:
            return False, "onnx or onnxruntime.transformers not available"
        except Exception as e:
            return False, f"Float16 conversion failed: {str(e)}"


# =============================================================================
# Local-First Service
# =============================================================================

class LocalFirstService:
    """
    Main service for local-first AI inference.
    
    This service manages the complete lifecycle of local AI execution:
    - Model loading and optimization
    - Inference with fallback support
    - Memory and resource management
    - Resilience patterns
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        enable_fallbacks: bool = True,
    ):
        self.model_manager = ONNXModelManager(model_dir)
        self.optimizer = ONNXOptimizer()
        self.enable_fallbacks = enable_fallbacks
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the local-first service."""
        if self._initialized:
            return
        
        # Pre-load any critical models here
        logger.info("Local-first service initialized")
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown the service and cleanup resources."""
        self.model_manager.unload_all()
        self._initialized = False
        logger.info("Local-first service shutdown complete")
    
    def load_model(
        self,
        model_path: Path,
        model_name: str,
        precision: ModelPrecision = ModelPrecision.FLOAT32,
        size_variant: ModelSize = ModelSize.MEDIUM,
        memory_mb: int = 512,
    ) -> Tuple[bool, Optional[str]]:
        """Load a model for inference."""
        config = ModelConfig(
            model_path=model_path,
            model_name=model_name,
            precision=precision,
            size_variant=size_variant,
            memory_mb=memory_mb,
        )
        return self.model_manager.load_model(config)
    
    def infer(
        self,
        model_name: str,
        inputs: Dict[str, np.ndarray],
        fallback_type: Optional[str] = None,
        fallback_input: Optional[Any] = None,
    ) -> InferenceResult:
        """Run inference with optional fallback."""
        if not self.enable_fallbacks:
            fallback_type = None
            fallback_input = None
        
        return self.model_manager.infer(
            model_name, inputs, fallback_type, fallback_input
        )
    
    def run_fallback(
        self,
        input_data: Any,
        input_type: str,
        context: Optional[Dict] = None,
    ) -> Tuple[Any, str]:
        """Run fallback strategy directly."""
        return self.model_manager._fallback_manager.execute(
            input_data, input_type, context
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        resources = self.model_manager._memory_manager.get_system_resources()
        return {
            "initialized": self._initialized,
            "loaded_models": self.model_manager.list_models(),
            "circuit_breaker_state": self.model_manager.circuit_breaker_state.value,
            "available_ram_mb": resources.available_ram_mb,
            "cpu_count": resources.cpu_count,
            "optimal_threads": self.model_manager._memory_manager.get_optimal_thread_count(),
        }
    
    @contextmanager
    def model_context(
        self,
        model_path: Path,
        model_name: str,
        **kwargs,
    ):
        """
        Context manager for temporary model loading.
        
        Automatically unloads the model when done.
        """
        try:
            success, error = self.load_model(model_path, model_name, **kwargs)
            if not success:
                raise RuntimeError(f"Failed to load model: {error}")
            yield self
        finally:
            self.model_manager._unload_model(model_name)


# Singleton instance
_local_first_service: Optional[LocalFirstService] = None


def get_local_first_service() -> LocalFirstService:
    """Get the singleton local-first service instance."""
    global _local_first_service
    if _local_first_service is None:
        _local_first_service = LocalFirstService()
    return _local_first_service

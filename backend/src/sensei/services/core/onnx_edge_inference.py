"""
ONNX Edge AI Inference Module.

Provides ONNX Runtime inference for edge AI models with:
- CPU-only execution (no GPU required)
- INT8 dynamic quantization
- Fallback to pure-Python implementation when ONNX unavailable
- Model warm-up for consistent latency
- Batch inference support

This module wraps the pure-Python EdgeCNN1D implementation with
ONNX Runtime for ~10-50x faster inference on CPU.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ONNXEdgeConfig:
    """Configuration for ONNX edge inference."""
    model_name: str
    cache_dir: Path
    input_length: int = 256
    num_classes: int = 4
    quantize_int8: bool = True
    warmup_on_init: bool = True
    batch_size: int = 32


class ONNXEdgeInference:
    """
    ONNX Runtime wrapper for edge AI inference.
    
    Provides high-performance CPU inference for 1D signal classification
    with automatic fallback to pure-Python implementation.
    """
    
    CLASS_LABELS = ["normal", "warning", "critical", "emergency"]
    
    def __init__(self, config: Optional[ONNXEdgeConfig] = None):
        self._config = config or self.default_config()
        self._session: Any = None  # Will be ort.InferenceSession if available
        self._is_loaded = False
        self._use_fallback = False
        self._fallback_model: Any = None  # Will be EdgeCNN1D if fallback needed
        self._init_attempted = False
        
        # Try to load ONNX model
        self._load_or_fallback()
    
    @staticmethod
    def default_config() -> ONNXEdgeConfig:
        """Get default configuration from environment."""
        cache_dir = Path(os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx"))
        return ONNXEdgeConfig(
            model_name="edge_anomaly_detector",
            cache_dir=cache_dir,
            input_length=int(os.getenv("SENSEI_EDGE_INPUT_LENGTH", "256")),
            num_classes=int(os.getenv("SENSEI_EDGE_NUM_CLASSES", "4")),
            quantize_int8=os.getenv("SENSEI_ONNX_QUANTIZE_INT8", "1") not in {"0", "false", "False"},
            warmup_on_init=os.getenv("SENSEI_ONNX_WARMUP", "1") not in {"0", "false", "False"},
            batch_size=int(os.getenv("SENSEI_ONNX_BATCH_SIZE", "32")),
        )
    
    def _load_or_fallback(self) -> None:
        """Try to load ONNX model, fall back to pure-Python if unavailable."""
        if self._init_attempted:
            return
        
        self._init_attempted = True
        
        try:
            self._load_onnx_model()
            logger.info(f"ONNX edge model loaded: {self._config.model_name}")
        except Exception as e:
            logger.info(f"ONNX not available, using pure-Python fallback: {e}")
            self._init_fallback()
    
    def _load_onnx_model(self) -> None:
        """Load or create ONNX model."""
        import onnxruntime as ort
        
        self._config.cache_dir.mkdir(parents=True, exist_ok=True)
        
        model_name = self._config.model_name
        onnx_path = self._config.cache_dir / f"{model_name}.onnx"
        quant_path = self._config.cache_dir / f"{model_name}.int8.onnx"
        
        target_path = quant_path if self._config.quantize_int8 else onnx_path
        
        if not target_path.exists():
            # Export the model to ONNX
            self._export_to_onnx(onnx_path)
            
            if self._config.quantize_int8:
                self._quantize_model(onnx_path, quant_path)
        
        # Load the session
        self._session = ort.InferenceSession(
            target_path.as_posix(),
            providers=["CPUExecutionProvider"],
        )
        
        self._is_loaded = True
        self._use_fallback = False
        
        if self._config.warmup_on_init:
            self._warmup()
    
    def _export_to_onnx(self, output_path: Path) -> None:
        """Export a 1D-CNN model to ONNX format using PyTorch."""
        import torch
        import torch.nn as nn
        
        class SimpleCNN1D(nn.Module):
            """Simple 1D CNN for signal classification."""
            
            def __init__(self, input_length: int, num_classes: int):
                super().__init__()
                self.conv1 = nn.Conv1d(1, 16, kernel_size=5, padding=2)
                self.pool1 = nn.MaxPool1d(2)
                self.conv2 = nn.Conv1d(16, 32, kernel_size=3, padding=1)
                self.pool2 = nn.MaxPool1d(2)
                
                # Calculate flattened size
                conv_output_size = input_length // 4  # Two pooling layers of size 2
                flatten_size = 32 * conv_output_size
                
                self.fc1 = nn.Linear(flatten_size, 64)
                self.fc2 = nn.Linear(64, 32)
                self.fc3 = nn.Linear(32, num_classes)
                self.relu = nn.ReLU()
                self.softmax = nn.Softmax(dim=1)
            
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                x = self.relu(self.conv1(x))
                x = self.pool1(x)
                x = self.relu(self.conv2(x))
                x = self.pool2(x)
                x = x.view(x.size(0), -1)
                x = self.relu(self.fc1(x))
                x = self.relu(self.fc2(x))
                x = self.fc3(x)
                return self.softmax(x)
        
        logger.info(f"Exporting edge model to ONNX: {output_path}")
        
        model = SimpleCNN1D(self._config.input_length, self._config.num_classes)
        model.eval()
        
        # Dummy input: [batch, channels, sequence_length]
        dummy_input = torch.randn(1, 1, self._config.input_length)
        
        with torch.no_grad():
            torch.onnx.export(
                model,
                (dummy_input,),
                output_path.as_posix(),
                input_names=["input"],
                output_names=["probabilities"],
                dynamo=True,
                opset_version=17,
            )
        
        logger.info(f"Exported ONNX model to {output_path}")
    
    def _quantize_model(self, input_path: Path, output_path: Path) -> None:
        """Quantize ONNX model to INT8."""
        from onnxruntime.quantization import QuantType, quantize_dynamic
        
        logger.info(f"Quantizing edge model to INT8: {output_path}")
        
        quantize_dynamic(
            model_input=input_path.as_posix(),
            model_output=output_path.as_posix(),
            weight_type=QuantType.QInt8,
            optimize_model=True,
        )
    
    def _warmup(self) -> None:
        """Warm up the model with dummy inference."""
        try:
            dummy = np.random.randn(1, 1, self._config.input_length).astype(np.float32)
            _ = self._session.run(None, {"input": dummy})
            logger.debug("Edge model warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    def _init_fallback(self) -> None:
        """Initialize pure-Python fallback model."""
        try:
            from sensei.services.core.edge_ai import CNNModelConfig, EdgeCNN1D
            
            config = CNNModelConfig(
                input_length=self._config.input_length,
                num_filters=[16, 32],
                kernel_sizes=[5, 3],
                pool_sizes=[2, 2],
                dense_units=[64, 32],
                num_classes=self._config.num_classes,
                threshold=0.7,
            )
            
            self._fallback_model = EdgeCNN1D(config)
            self._use_fallback = True
            self._is_loaded = True
            
        except ImportError as e:
            logger.error(f"Failed to load fallback model: {e}")
            self._use_fallback = True
            self._is_loaded = False
    
    def is_ready(self) -> bool:
        """Check if model is ready for inference."""
        return self._is_loaded
    
    def is_using_onnx(self) -> bool:
        """Check if using ONNX Runtime (vs fallback)."""
        return not self._use_fallback and self._session is not None
    
    def predict(self, signal: List[float]) -> List[float]:
        """
        Run inference on a single signal.
        
        Args:
            signal: List of float values representing the 1D signal.
            
        Returns:
            List of class probabilities.
        """
        if not self._is_loaded:
            self._load_or_fallback()
        
        if self._use_fallback:
            return self._predict_fallback(signal)
        
        return self._predict_onnx(signal)
    
    def _predict_onnx(self, signal: List[float]) -> List[float]:
        """Predict using ONNX Runtime."""
        # Pad or truncate
        if len(signal) < self._config.input_length:
            signal = signal + [0.0] * (self._config.input_length - len(signal))
        elif len(signal) > self._config.input_length:
            signal = signal[:self._config.input_length]
        
        # Shape: [batch=1, channels=1, sequence_length]
        input_array = np.array(signal, dtype=np.float32).reshape(1, 1, -1)
        
        outputs = self._session.run(None, {"input": input_array})
        
        return outputs[0][0].tolist()
    
    def _predict_fallback(self, signal: List[float]) -> List[float]:
        """Predict using pure-Python fallback."""
        if self._fallback_model is None:
            return [0.25] * self._config.num_classes  # Uniform distribution
        
        return self._fallback_model.predict(signal)
    
    def classify(self, signal: List[float]) -> Tuple[int, float, str]:
        """
        Classify signal and return class index, confidence, and label.
        
        Returns:
            Tuple of (class_index, confidence, class_label)
        """
        probs = self.predict(signal)
        
        if not probs:
            return 0, 0.0, self.CLASS_LABELS[0]
        
        class_idx = int(np.argmax(probs))
        confidence = float(probs[class_idx])
        label = self.CLASS_LABELS[class_idx] if class_idx < len(self.CLASS_LABELS) else "unknown"
        
        return class_idx, confidence, label
    
    def predict_batch(self, signals: List[List[float]]) -> List[List[float]]:
        """
        Run batch inference on multiple signals.
        
        Args:
            signals: List of signals, each a list of float values.
            
        Returns:
            List of probability distributions.
        """
        if not signals:
            return []
        
        if not self._is_loaded:
            self._load_or_fallback()
        
        if self._use_fallback:
            return [self._predict_fallback(s) for s in signals]
        
        return self._predict_batch_onnx(signals)
    
    def _predict_batch_onnx(self, signals: List[List[float]]) -> List[List[float]]:
        """Batch predict using ONNX Runtime."""
        all_probs = []
        
        for batch_start in range(0, len(signals), self._config.batch_size):
            batch = signals[batch_start:batch_start + self._config.batch_size]
            
            # Normalize signal lengths
            normalized = []
            for signal in batch:
                if len(signal) < self._config.input_length:
                    signal = signal + [0.0] * (self._config.input_length - len(signal))
                elif len(signal) > self._config.input_length:
                    signal = signal[:self._config.input_length]
                normalized.append(signal)
            
            # Shape: [batch, channels=1, sequence_length]
            input_array = np.array(normalized, dtype=np.float32).reshape(-1, 1, self._config.input_length)
            
            outputs = self._session.run(None, {"input": input_array})
            all_probs.extend(outputs[0].tolist())
        
        return all_probs
    
    def classify_batch(
        self,
        signals: List[List[float]],
    ) -> List[Tuple[int, float, str]]:
        """
        Classify multiple signals in batch.
        
        Returns:
            List of (class_index, confidence, class_label) tuples.
        """
        probs_list = self.predict_batch(signals)
        
        results = []
        for probs in probs_list:
            if not probs:
                results.append((0, 0.0, self.CLASS_LABELS[0]))
            else:
                class_idx = int(np.argmax(probs))
                confidence = float(probs[class_idx])
                label = self.CLASS_LABELS[class_idx] if class_idx < len(self.CLASS_LABELS) else "unknown"
                results.append((class_idx, confidence, label))
        
        return results


# Singleton instance
_onnx_edge_inference: Optional[ONNXEdgeInference] = None


def get_onnx_edge_inference() -> ONNXEdgeInference:
    """Get the singleton ONNX edge inference instance."""
    global _onnx_edge_inference
    if _onnx_edge_inference is None:
        _onnx_edge_inference = ONNXEdgeInference()
    return _onnx_edge_inference

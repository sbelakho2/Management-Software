"""ONNX Runtime embeddings (on-device).

This module provides a minimal, production-oriented path to generate sentence
embeddings using a locally-exported Transformer encoder in ONNX format.

Key goals:
- On-device inference via ONNX Runtime
- Optional dynamic INT8 quantization for CPU efficiency
- Safe caching of exported/quantized artifacts on disk

Notes:
- Model export requires `torch` and `transformers`.
- Quantization requires `onnxruntime`.
- First run may download model weights from Hugging Face if not present in cache.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    model_id: str
    cache_dir: Path
    quantize_int8: bool = True
    max_length: int = 256


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(v, axis=-1, keepdims=True)
    denom = np.maximum(denom, 1e-12)
    return v / denom


def _mean_pool(last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    mask = attention_mask.astype(np.float32)
    mask = np.expand_dims(mask, axis=-1)
    summed = (last_hidden_state * mask).sum(axis=1)
    counts = np.maximum(mask.sum(axis=1), 1e-6)
    return summed / counts


class ONNXTextEmbedder:
    """Sentence embedding generator backed by ONNX Runtime."""

    def __init__(self, config: EmbeddingConfig):
        self._config = config
        self._session = None
        self._tokenizer = None

    @staticmethod
    def default_config() -> EmbeddingConfig:
        cache_dir = Path(os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx"))
        return EmbeddingConfig(
            model_id=os.getenv("SENSEI_ONNX_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            cache_dir=cache_dir,
            quantize_int8=os.getenv("SENSEI_ONNX_QUANTIZE_INT8", "1") not in {"0", "false", "False"},
            max_length=int(os.getenv("SENSEI_ONNX_MAX_LENGTH", "256")),
        )

    def is_ready(self) -> bool:
        """True if we can generate embeddings (dependencies installed)."""
        try:
            import onnxruntime  # noqa: F401
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except Exception:
            return False
        return True

    def _ensure_loaded(self) -> None:
        if self._session is not None and self._tokenizer is not None:
            return

        # Local imports keep module import cheap.
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError:
            # Fallback not really supported here but let's not crash
            return

        from sensei.services.ai.onnx_model_init import get_model_registry

        self._config.cache_dir.mkdir(parents=True, exist_ok=True)
        model_slug = self._config.model_id.replace("/", "__")
        onnx_path = self._config.cache_dir / f"{model_slug}.onnx"
        quant_path = self._config.cache_dir / f"{model_slug}.int8.onnx"

        # Use registry to verify path if possible
        registry = get_model_registry()
        model_paths = registry.get_model_paths()
        target_path = quant_path if self._config.quantize_int8 else onnx_path
        
        # Override target if registry has a specific path for 'embeddings'
        if "embeddings" in model_paths:
            reg_path = model_paths["embeddings"]
            if reg_path.name == target_path.name:
                target_path = reg_path

        if not target_path.exists():
            try:
                import torch
                from transformers import AutoModel
            except ImportError:
                return

            tokenizer = AutoTokenizer.from_pretrained(self._config.model_id, local_files_only=False)

            # Export base ONNX if missing
            if not onnx_path.exists():
                model = AutoModel.from_pretrained(self._config.model_id)
                model.eval()

                # Dummy inputs for export
                dummy = tokenizer(
                    "dummy input",
                    return_tensors="pt",
                    max_length=min(32, self._config.max_length),
                    truncation=True,
                    padding="max_length",
                )
                input_names = ["input_ids", "attention_mask"]
                inputs = (dummy["input_ids"], dummy["attention_mask"])

                dynamic_axes = {
                    "input_ids": {0: "batch", 1: "sequence"},
                    "attention_mask": {0: "batch", 1: "sequence"},
                    "last_hidden_state": {0: "batch", 1: "sequence"},
                }

                with torch.no_grad():
                    torch.onnx.export(
                        model,
                        inputs,
                        onnx_path.as_posix(),
                        input_names=input_names,
                        output_names=["last_hidden_state"],
                        dynamic_axes=dynamic_axes,
                        opset_version=17,
                    )

            if self._config.quantize_int8:
                from onnxruntime.quantization import QuantType, quantize_dynamic

                quantize_dynamic(
                    model_input=onnx_path.as_posix(),
                    model_output=quant_path.as_posix(),
                    weight_type=QuantType.QInt8,
                )

        tokenizer = AutoTokenizer.from_pretrained(self._config.model_id, local_files_only=False)
        sess = ort.InferenceSession(
            target_path.as_posix(),
            providers=["CPUExecutionProvider"],
        )

        self._tokenizer = tokenizer
        self._session = sess

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        self._ensure_loaded()
        assert self._session is not None
        assert self._tokenizer is not None

        texts_list = list(texts)
        if not texts_list:
            return []

        batch = self._tokenizer(
            texts_list,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=self._config.max_length,
        )

        outputs = self._session.run(
            None,
            {
                "input_ids": batch["input_ids"].astype(np.int64),
                "attention_mask": batch["attention_mask"].astype(np.int64),
            },
        )

        # Expected: last_hidden_state [batch, seq, hidden]
        last_hidden_state = outputs[0]
        pooled = _mean_pool(last_hidden_state, batch["attention_mask"])
        pooled = _l2_normalize(pooled)
        return pooled.astype(np.float32).tolist()

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


# Singleton
_onnx_embedder: ONNXTextEmbedder | None = None


def get_onnx_embedder() -> ONNXTextEmbedder:
    global _onnx_embedder
    if _onnx_embedder is None:
        _onnx_embedder = ONNXTextEmbedder(ONNXTextEmbedder.default_config())
    return _onnx_embedder

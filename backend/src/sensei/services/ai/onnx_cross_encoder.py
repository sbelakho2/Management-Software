"""ONNX Cross-Encoder Re-ranker for Hybrid Search.

This module provides a production-ready cross-encoder re-ranker using ONNX Runtime
for CPU-efficient inference without GPU requirements.

Key features:
- On-device inference via ONNX Runtime (CPU only)
- Dynamic INT8 quantization for efficiency
- Result caching with TTL
- Fallback to TF-IDF scoring when ONNX unavailable
- Model warm-up on initialization

Supported models:
- BAAI/bge-reranker-base (default)
- cross-encoder/ms-marco-MiniLM-L-6-v2
- sentence-transformers/cross-encoder-ms-marco-TinyBERT-L-2-v2
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Shared thread pool for ONNX cross-encoder inference (avoids blocking the event loop)
_xenc_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="onnx-xenc")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class CrossEncoderConfig:
    """Configuration for the ONNX cross-encoder."""
    model_id: str
    cache_dir: Path
    quantize_int8: bool = True
    max_length: int = 512
    cache_ttl_seconds: int = 3600  # 1 hour
    warmup_on_init: bool = True
    batch_size: int = 32


@dataclass
class RerankCacheEntry:
    """Cached re-ranking score entry."""
    score: float
    created_at: datetime
    expires_at: datetime


class CrossEncoderCache:
    """Redis-backed cache for cross-encoder scores with in-memory LRU fallback.

    Uses Redis as the primary store for cross-instance consistency. Falls back
    to an in-memory dict (bounded to prevent OOM) if Redis is unavailable.
    """
    
    _REDIS_PREFIX = "sensei:xenc:"
    _MAX_MEMORY_ENTRIES = 10000  # Cap in-memory fallback to prevent OOM
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, RerankCacheEntry] = {}
        self._redis_available: Optional[bool] = None
    
    def _make_key(self, query: str, context: str) -> str:
        """Create cache key from query and context."""
        combined = f"{query}|||{context}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    async def _check_redis(self) -> bool:
        """Lazily check if Redis is available."""
        if self._redis_available is not None:
            return self._redis_available
        try:
            from sensei.core.redis import redis_client
            await redis_client.ping()
            self._redis_available = True
        except Exception:
            self._redis_available = False
        return self._redis_available

    def get(self, query: str, context: str) -> Optional[float]:
        """Get cached score from in-memory fallback (sync path)."""
        key = self._make_key(query, context)
        entry = self._cache.get(key)
        
        if entry and entry.expires_at > _utcnow():
            return entry.score
        
        # Clean up expired entry
        if entry:
            del self._cache[key]
        
        return None

    async def aget(self, query: str, context: str) -> Optional[float]:
        """Get cached score from Redis (async path), fallback to in-memory."""
        key = self._make_key(query, context)
        if await self._check_redis():
            try:
                from sensei.core.redis import redis_client
                val = await redis_client.get(f"{self._REDIS_PREFIX}{key}")
                if val is not None:
                    return float(val)
            except Exception:
                pass
        return self.get(query, context)
    
    def set(self, query: str, context: str, score: float) -> None:
        """Cache a re-ranking score in memory."""
        key = self._make_key(query, context)
        now = _utcnow()
        
        # Enforce memory cap
        if len(self._cache) >= self._MAX_MEMORY_ENTRIES:
            # Remove oldest 20% of entries
            to_remove = sorted(self._cache.items(), key=lambda x: x[1].created_at)[:self._MAX_MEMORY_ENTRIES // 5]
            for k, _ in to_remove:
                del self._cache[k]
        
        entry = RerankCacheEntry(
            score=score,
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self._cache[key] = entry

    async def aset(self, query: str, context: str, score: float) -> None:
        """Cache a re-ranking score in Redis + memory."""
        key = self._make_key(query, context)
        self.set(query, context, score)
        if await self._check_redis():
            try:
                from sensei.core.redis import redis_client
                await redis_client.setex(f"{self._REDIS_PREFIX}{key}", self.ttl_seconds, str(score))
            except Exception:
                pass
    
    def clear_expired(self) -> int:
        """Clear expired entries. Returns count removed."""
        now = _utcnow()
        expired = [k for k, v in self._cache.items() if v.expires_at <= now]
        
        for key in expired:
            del self._cache[key]
        
        return len(expired)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Return cache size."""
        return len(self._cache)


class TFIDFScorer:
    """Fallback TF-IDF based scoring when ONNX is unavailable."""
    
    def __init__(self):
        self._idf_cache: Dict[str, float] = {}
    
    def score(self, query: str, context: str) -> float:
        """Score a query-context pair using TF-IDF-like scoring."""
        # Tokenize
        query_terms = set(self._tokenize(query))
        context_terms = self._tokenize(context)
        
        if not query_terms or not context_terms:
            return 0.0
        
        # Calculate term frequencies in context
        context_tf: Dict[str, int] = {}
        for term in context_terms:
            context_tf[term] = context_tf.get(term, 0) + 1
        
        # Calculate BM25-like score
        k1 = 1.2
        b = 0.75
        avg_dl = 200  # Assumed average document length
        dl = len(context_terms)
        
        score = 0.0
        for term in query_terms:
            if term in context_tf:
                tf = context_tf[term]
                # Simplified IDF (would need corpus stats for real IDF)
                idf = 1.0  # Placeholder
                
                # BM25 term score
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (dl / avg_dl))
                score += idf * (numerator / denominator)
        
        # Normalize to [0, 1] range
        max_possible = len(query_terms) * (k1 + 1)
        normalized = score / max_possible if max_possible > 0 else 0.0
        
        # Additional boost for exact phrase matches
        if query.lower() in context.lower():
            normalized = min(1.0, normalized + 0.2)
        
        return min(1.0, max(0.0, normalized))
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        text = text.lower()
        # Use \w+ for unicode-aware word matching
        terms = re.findall(r'\w+', text)
        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                     'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
                     'can', 'just', 'now', 'it', 'its', 'this', 'that', 'these',
                     'those', 'there', 'here', 'where', 'when', 'why', 'how', 'all',
                     'each', 'every', 'any', 'some', 'no', 'such', 'what', 'which',
                     'who', 'whom', 'whose'}
        return [t for t in terms if t not in stopwords and len(t) > 1]


class ONNXCrossEncoder:
    """
    Production-ready ONNX-based cross-encoder for re-ranking.
    
    This uses a cross-encoder model to score query-document relevance.
    Falls back to TF-IDF scoring if ONNX runtime is unavailable.
    """
    
    def __init__(self, config: Optional[CrossEncoderConfig] = None):
        self._config = config or self.default_config()
        self._session = None
        self._tokenizer = None
        self._is_loaded = False
        self._fallback = TFIDFScorer()
        self._cache = CrossEncoderCache(self._config.cache_ttl_seconds)
        self._use_fallback = False
        
        # Track initialization state
        self._init_attempted = False
        self._init_error: Optional[str] = None
    
    @staticmethod
    def default_config() -> CrossEncoderConfig:
        """Get default configuration from environment."""
        cache_dir = Path(os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx"))
        return CrossEncoderConfig(
            model_id=os.getenv(
                "SENSEI_ONNX_RERANKER_MODEL",
                "cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
            cache_dir=cache_dir,
            quantize_int8=os.getenv("SENSEI_ONNX_QUANTIZE_INT8", "1") not in {"0", "false", "False"},
            max_length=int(os.getenv("SENSEI_ONNX_RERANKER_MAX_LENGTH", "512")),
            cache_ttl_seconds=int(os.getenv("SENSEI_ONNX_CACHE_TTL", "3600")),
            warmup_on_init=os.getenv("SENSEI_ONNX_WARMUP", "1") not in {"0", "false", "False"},
            batch_size=int(os.getenv("SENSEI_ONNX_BATCH_SIZE", "32")),
        )
    
    def is_ready(self) -> bool:
        """Check if ONNX dependencies are available."""
        try:
            import onnxruntime  # noqa: F401
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded
    
    def _ensure_loaded(self) -> bool:
        """Ensure model is loaded. Returns True if using ONNX, False if fallback."""
        if self._is_loaded:
            return not self._use_fallback
        
        if self._init_attempted:
            return not self._use_fallback
        
        self._init_attempted = True
        
        try:
            try:
                import onnxruntime as ort
                from transformers import AutoTokenizer
            except ImportError as e:
                logger.warning(f"Required libraries for ONNX not found: {e}")
                self._use_fallback = True
                self._is_loaded = True
                return False

            self._config.cache_dir.mkdir(parents=True, exist_ok=True)
            model_slug = self._config.model_id.replace("/", "__")
            onnx_path = self._config.cache_dir / f"{model_slug}_reranker.onnx"
            quant_path = self._config.cache_dir / f"{model_slug}_reranker.int8.onnx"
            
            target_path = quant_path if self._config.quantize_int8 else onnx_path
            
            if not target_path.exists():
                logger.info(f"Attempting to export cross-encoder model to ONNX: {self._config.model_id}")
                
                try:
                    import torch
                    from transformers import AutoModelForSequenceClassification
                except ImportError:
                    logger.warning("torch or transformers not available for ONNX export, using fallback")
                    self._use_fallback = True
                    self._is_loaded = True
                    return False

                tokenizer = AutoTokenizer.from_pretrained(self._config.model_id)

                # Export base ONNX if missing
                if not onnx_path.exists():
                    model = AutoModelForSequenceClassification.from_pretrained(self._config.model_id)
                    model.eval()
                    
                    # Dummy inputs for export
                    dummy = tokenizer(
                        "query text",
                        "document text",
                        return_tensors="pt",
                        max_length=min(64, self._config.max_length),
                        truncation=True,
                        padding="max_length",
                    )
                    
                    input_names = ["input_ids", "attention_mask", "token_type_ids"]
                    inputs = (
                        dummy["input_ids"],
                        dummy["attention_mask"],
                        dummy.get("token_type_ids", torch.zeros_like(dummy["input_ids"])),
                    )
                    
                    dynamic_axes = {
                        "input_ids": {0: "batch", 1: "sequence"},
                        "attention_mask": {0: "batch", 1: "sequence"},
                        "token_type_ids": {0: "batch", 1: "sequence"},
                        "logits": {0: "batch"},
                    }
                    
                    with torch.no_grad():
                        torch.onnx.export(
                            model,
                            inputs,
                            onnx_path.as_posix(),
                            input_names=input_names,
                            output_names=["logits"],
                            dynamic_axes=dynamic_axes,
                            opset_version=17,
                        )
                    
                    logger.info(f"Exported ONNX model to {onnx_path}")
                
                if self._config.quantize_int8:
                    from onnxruntime.quantization import QuantType, quantize_dynamic
                    
                    logger.info(f"Quantizing model to INT8: {quant_path}")
                    quantize_dynamic(
                        model_input=onnx_path.as_posix(),
                        model_output=quant_path.as_posix(),
                        weight_type=QuantType.QInt8,
                        optimize_model=True,
                    )

            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(self._config.model_id)
            
            # Load the session with graph optimizations
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 2  # Limit threads for VPS
            sess_options.inter_op_num_threads = 1
            sess_options.enable_mem_pattern = True
            sess_options.enable_cpu_mem_arena = True
            sess = ort.InferenceSession(
                target_path.as_posix(),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            
            self._tokenizer = tokenizer
            self._session = sess
            self._is_loaded = True
            self._use_fallback = False
            
            # Warm up
            if self._config.warmup_on_init:
                self._warmup()
            
            logger.info(f"ONNX cross-encoder loaded successfully: {self._config.model_id}")
            return True
            
        except Exception as e:
            self._init_error = str(e)
            self._use_fallback = True
            self._is_loaded = True
            logger.warning(f"Failed to load ONNX cross-encoder, using fallback: {e}")
            return False
    
    def _warmup(self) -> None:
        """Warm up the model with dummy inference."""
        try:
            _ = self.score_pair("warmup query", "warmup document context")
            logger.debug("Cross-encoder warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    def score_pair(self, query: str, context: str) -> float:
        """
        Score a single query-context pair.
        
        Returns a relevance score between 0 and 1.
        """
        # Check cache
        cached = self._cache.get(query, context)
        if cached is not None:
            return cached
        
        # Ensure model is loaded
        using_onnx = self._ensure_loaded()
        
        if not using_onnx or self._use_fallback:
            score = self._fallback.score(query, context)
        else:
            score = self._score_with_onnx(query, context)
        
        # Cache result
        self._cache.set(query, context, score)
        
        return score
    
    def _score_with_onnx(self, query: str, context: str) -> float:
        """Score using ONNX model."""
        assert self._session is not None
        assert self._tokenizer is not None
        
        # Tokenize the pair
        encoded = self._tokenizer(
            query,
            context,
            return_tensors="np",
            max_length=self._config.max_length,
            truncation=True,
            padding="max_length",
        )
        
        # Prepare inputs
        inputs = {
            "input_ids": encoded["input_ids"].astype(np.int64),
            "attention_mask": encoded["attention_mask"].astype(np.int64),
        }
        
        # Add token_type_ids if available
        if "token_type_ids" in encoded:
            inputs["token_type_ids"] = encoded["token_type_ids"].astype(np.int64)
        else:
            # Create zeros for models that expect it
            inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
        
        # Run inference
        outputs = self._session.run(None, inputs)
        
        # Get logits and convert to probability
        logits = outputs[0]
        
        # For binary relevance, sigmoid
        if logits.shape[-1] == 1:
            score = 1.0 / (1.0 + np.exp(-logits[0, 0]))
        else:
            # For multi-class, softmax on positive class
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)
            score = float(probs[0, -1])  # Last class is typically "relevant"
        
        return float(score)
    
    def score_pairs_batch(
        self,
        query: str,
        contexts: List[str],
    ) -> List[float]:
        """
        Score multiple query-context pairs efficiently.
        
        Uses batching for ONNX inference.
        """
        if not contexts:
            return []
        
        # Check cache for all
        scores = []
        uncached_indices = []
        uncached_contexts = []
        
        for i, context in enumerate(contexts):
            cached = self._cache.get(query, context)
            if cached is not None:
                scores.append((i, cached))
            else:
                uncached_indices.append(i)
                uncached_contexts.append(context)
        
        # Score uncached items
        if uncached_contexts:
            using_onnx = self._ensure_loaded()
            
            if not using_onnx or self._use_fallback:
                # Score individually with fallback
                for i, context in zip(uncached_indices, uncached_contexts):
                    score = self._fallback.score(query, context)
                    self._cache.set(query, context, score)
                    scores.append((i, score))
            else:
                # Batch scoring with ONNX
                batch_scores = self._score_batch_with_onnx(query, uncached_contexts)
                for i, context, score in zip(uncached_indices, uncached_contexts, batch_scores):
                    self._cache.set(query, context, score)
                    scores.append((i, score))
        
        # Sort by original index and extract scores
        scores.sort(key=lambda x: x[0])
        return [s for _, s in scores]
    
    def _score_batch_with_onnx(self, query: str, contexts: List[str]) -> List[float]:
        """Score a batch of contexts against a query using ONNX."""
        assert self._session is not None
        assert self._tokenizer is not None
        
        all_scores = []
        
        # Process in batches
        for batch_start in range(0, len(contexts), self._config.batch_size):
            batch_contexts = contexts[batch_start:batch_start + self._config.batch_size]
            
            # Tokenize all pairs
            queries = [query] * len(batch_contexts)
            encoded = self._tokenizer(
                queries,
                batch_contexts,
                return_tensors="np",
                max_length=self._config.max_length,
                truncation=True,
                padding=True,
            )
            
            # Prepare inputs
            inputs = {
                "input_ids": encoded["input_ids"].astype(np.int64),
                "attention_mask": encoded["attention_mask"].astype(np.int64),
            }
            
            if "token_type_ids" in encoded:
                inputs["token_type_ids"] = encoded["token_type_ids"].astype(np.int64)
            else:
                inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
            
            # Run inference
            outputs = self._session.run(None, inputs)
            logits = outputs[0]
            
            # Convert to scores
            if logits.shape[-1] == 1:
                batch_scores = (1.0 / (1.0 + np.exp(-logits[:, 0]))).tolist()
            else:
                exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
                probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)
                batch_scores = probs[:, -1].tolist()
            
            all_scores.extend(batch_scores)
        
        return all_scores
    
    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, Any]],  # List of (content, metadata)
        top_k: int = 10,
    ) -> List[Tuple[str, Any, float]]:
        """
        Re-rank documents by relevance to query.
        
        Args:
            query: Search query
            documents: List of (content, metadata) tuples
            top_k: Number of top results to return
            
        Returns:
            List of (content, metadata, score) tuples, sorted by score descending
        """
        if not documents:
            return []
        
        contents = [doc[0] for doc in documents]
        scores = self.score_pairs_batch(query, contents)
        
        # Combine with metadata
        results = [
            (doc[0], doc[1], score)
            for doc, score in zip(documents, scores)
        ]
        
        # Sort by score descending
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results[:top_k]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": self._cache.size(),
            "ttl_seconds": self._config.cache_ttl_seconds,
        }
    
    def clear_cache(self) -> int:
        """Clear the cache. Returns number of entries cleared."""
        size = self._cache.size()
        self._cache.clear()
        return size

    async def ascore_pair(self, query: str, context: str) -> float:
        """Async version of score_pair that offloads to thread pool.

        Use this from async endpoints to avoid blocking the event loop
        during ONNX inference.
        """
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_xenc_executor, self.score_pair, query, context)

    async def arerank(
        self,
        query: str,
        documents: List[Tuple[str, Any]],
        top_k: int = 10,
    ) -> List[Tuple[str, Any, float]]:
        """Async version of rerank that offloads to thread pool."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _xenc_executor, self.rerank, query, documents, top_k
        )


# Singleton instance
_cross_encoder: Optional[ONNXCrossEncoder] = None


def get_cross_encoder() -> ONNXCrossEncoder:
    """Get the singleton cross-encoder instance."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = ONNXCrossEncoder()
    return _cross_encoder

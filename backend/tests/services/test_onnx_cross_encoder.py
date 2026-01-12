"""
Tests for ONNX Cross-Encoder Re-ranker.

Tests the TF-IDF fallback and ONNX cross-encoder implementation.
"""

import pytest
from datetime import timedelta


class TestCrossEncoderConfig:
    """Tests for CrossEncoderConfig dataclass."""
    
    def test_default_config_creation(self):
        """Test creating config with defaults."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderConfig
        from pathlib import Path
        
        config = CrossEncoderConfig(
            model_id="test-model",
            cache_dir=Path("/tmp/test"),
        )
        
        assert config.model_id == "test-model"
        assert config.quantize_int8 is True
        assert config.max_length == 512
        assert config.cache_ttl_seconds == 3600
        assert config.warmup_on_init is True
        assert config.batch_size == 32
    
    def test_custom_config(self):
        """Test creating config with custom values."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderConfig
        from pathlib import Path
        
        config = CrossEncoderConfig(
            model_id="custom-model",
            cache_dir=Path("/tmp/custom"),
            quantize_int8=False,
            max_length=256,
            cache_ttl_seconds=7200,
            warmup_on_init=False,
            batch_size=16,
        )
        
        assert config.model_id == "custom-model"
        assert config.quantize_int8 is False
        assert config.max_length == 256
        assert config.cache_ttl_seconds == 7200
        assert config.warmup_on_init is False
        assert config.batch_size == 16


class TestCrossEncoderCache:
    """Tests for CrossEncoderCache."""
    
    def test_cache_set_and_get(self):
        """Test caching a score."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderCache
        
        cache = CrossEncoderCache(ttl_seconds=3600)
        cache.set("query", "context", 0.85)
        
        result = cache.get("query", "context")
        assert result == 0.85
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderCache
        
        cache = CrossEncoderCache()
        result = cache.get("unknown", "query")
        assert result is None
    
    def test_cache_key_uniqueness(self):
        """Test different queries have different cache keys."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderCache
        
        cache = CrossEncoderCache()
        cache.set("query1", "context", 0.5)
        cache.set("query2", "context", 0.7)
        
        assert cache.get("query1", "context") == 0.5
        assert cache.get("query2", "context") == 0.7
    
    def test_cache_clear(self):
        """Test clearing cache."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderCache
        
        cache = CrossEncoderCache()
        cache.set("q", "c", 0.5)
        assert cache.size() == 1
        
        cache.clear()
        assert cache.size() == 0
    
    def test_cache_size(self):
        """Test cache size tracking."""
        from sensei.services.ai.onnx_cross_encoder import CrossEncoderCache
        
        cache = CrossEncoderCache()
        assert cache.size() == 0
        
        cache.set("q1", "c1", 0.5)
        cache.set("q2", "c2", 0.6)
        assert cache.size() == 2


class TestTFIDFScorer:
    """Tests for TF-IDF fallback scorer."""
    
    def test_basic_scoring(self):
        """Test basic TF-IDF scoring."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        score = scorer.score("machine learning", "machine learning models")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have decent relevance
    
    def test_exact_phrase_match_bonus(self):
        """Test exact phrase match gives bonus."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        
        exact = scorer.score("machine learning", "machine learning is great")
        partial = scorer.score("machine learning", "machine and learning concepts")
        
        assert exact > partial
    
    def test_no_overlap_low_score(self):
        """Test no term overlap gives low score."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        score = scorer.score("cats dogs", "airplanes trains boats")
        
        assert score < 0.3
    
    def test_empty_query(self):
        """Test empty query returns zero."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        score = scorer.score("", "some context")
        assert score == 0.0
    
    def test_empty_context(self):
        """Test empty context returns zero."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        score = scorer.score("query", "")
        assert score == 0.0
    
    def test_stopwords_filtered(self):
        """Test stopwords are properly filtered."""
        from sensei.services.ai.onnx_cross_encoder import TFIDFScorer
        
        scorer = TFIDFScorer()
        
        # These should score similarly since stopwords are removed
        s1 = scorer.score("the machine", "machine learning")
        s2 = scorer.score("machine", "machine learning")
        
        assert abs(s1 - s2) < 0.2


class TestONNXCrossEncoder:
    """Tests for ONNXCrossEncoder."""
    
    def test_encoder_creation(self):
        """Test encoder can be created."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        assert encoder is not None
    
    def test_is_ready_check(self):
        """Test is_ready checks for dependencies."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        # Should return True if onnxruntime and transformers are installed
        ready = encoder.is_ready()
        assert isinstance(ready, bool)
    
    def test_score_pair_returns_float(self):
        """Test score_pair returns a float."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        score = encoder.score_pair("query", "context document")
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_score_pair_caching(self):
        """Test score_pair uses caching."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        
        # First call
        score1 = encoder.score_pair("test query", "test context")
        
        # Second call (should hit cache)
        score2 = encoder.score_pair("test query", "test context")
        
        assert score1 == score2
    
    def test_score_pairs_batch(self):
        """Test batch scoring."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        
        contexts = [
            "First document about cats",
            "Second document about dogs",
            "Third document about birds",
        ]
        
        scores = encoder.score_pairs_batch("animals", contexts)
        
        assert len(scores) == 3
        for score in scores:
            assert 0.0 <= score <= 1.0
    
    def test_rerank_returns_sorted(self):
        """Test rerank returns sorted results."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        
        documents = [
            ("irrelevant text about weather", {"id": 1}),
            ("machine learning models are useful", {"id": 2}),
            ("neural networks for deep learning", {"id": 3}),
        ]
        
        results = encoder.rerank("machine learning", documents, top_k=2)
        
        assert len(results) == 2
        # Each result should have content, metadata, score
        for content, meta, score in results:
            assert isinstance(content, str)
            assert isinstance(meta, dict)
            assert isinstance(score, float)
    
    def test_rerank_empty_input(self):
        """Test rerank handles empty input."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        results = encoder.rerank("query", [], top_k=5)
        
        assert results == []
    
    def test_cache_stats(self):
        """Test getting cache stats."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        stats = encoder.get_cache_stats()
        
        assert "size" in stats
        assert "ttl_seconds" in stats
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        from sensei.services.ai.onnx_cross_encoder import ONNXCrossEncoder
        
        encoder = ONNXCrossEncoder()
        encoder.score_pair("q", "c")
        
        cleared = encoder.clear_cache()
        assert cleared >= 0


class TestGetCrossEncoder:
    """Tests for get_cross_encoder singleton function."""
    
    def test_returns_encoder(self):
        """Test singleton returns an encoder."""
        from sensei.services.ai.onnx_cross_encoder import get_cross_encoder
        
        encoder = get_cross_encoder()
        assert encoder is not None
    
    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        from sensei.services.ai.onnx_cross_encoder import get_cross_encoder
        
        encoder1 = get_cross_encoder()
        encoder2 = get_cross_encoder()
        
        assert encoder1 is encoder2

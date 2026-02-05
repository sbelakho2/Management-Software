"""
Local LLM Client - On-Device AI Only

Provides local LLM inference using:
1. llama.cpp (via llama-cpp-python) for quantized models
2. Transformers library for HuggingFace models
3. ONNX Runtime for optimized inference

NO external API calls - all processing on-device.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class LLMBackend(str, Enum):
    """Available LLM backends."""
    LLAMA_CPP = "llama_cpp"  # llama.cpp (quantized, fast)
    TRANSFORMERS = "transformers"  # HuggingFace Transformers
    ONNX = "onnx"  # ONNX Runtime


@dataclass
class LLMConfig:
    """Configuration for local LLM."""
    model_path: str
    backend: LLMBackend = LLMBackend.LLAMA_CPP
    context_length: int = 4096
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    n_gpu_layers: int = 0  # 0 = CPU only, >0 = use GPU
    n_threads: int = 4
    batch_size: int = 512
    use_mmap: bool = True
    use_mlock: bool = False


class BaseLLMClient(ABC):
    """Base class for LLM clients."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate completion for prompt."""
        pass
    
    @abstractmethod
    def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Stream completion tokens."""
        pass


class LlamaCppClient(BaseLLMClient):
    """LLM client using llama.cpp for fast quantized inference."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load model with llama.cpp."""
        try:
            from llama_cpp import Llama
            
            logger.info(f"Loading model from {self.config.model_path}")
            logger.info(f"GPU layers: {self.config.n_gpu_layers}, Threads: {self.config.n_threads}")
            
            self.model = Llama(
                model_path=self.config.model_path,
                n_ctx=self.config.context_length,
                n_threads=self.config.n_threads,
                n_gpu_layers=self.config.n_gpu_layers,
                n_batch=self.config.batch_size,
                use_mmap=self.config.use_mmap,
                use_mlock=self.config.use_mlock,
                verbose=False
            )
            
            logger.info(f"✓ Model loaded successfully")
            
        except ImportError:
            logger.error("llama-cpp-python not installed. Run: pip install llama-cpp-python")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate completion."""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        response = self.model(
            prompt,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            repeat_penalty=self.config.repeat_penalty,
            stop=stop or [],
            echo=False
        )
        
        return response['choices'][0]['text']
    
    def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Stream completion tokens."""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        stream = self.model(
            prompt,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            repeat_penalty=self.config.repeat_penalty,
            stop=stop or [],
            stream=True,
            echo=False
        )
        
        for chunk in stream:
            text = chunk['choices'][0]['text']
            if text:
                yield text


class TransformersClient(BaseLLMClient):
    """LLM client using HuggingFace Transformers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load model with Transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info(f"Loading model: {self.config.model_path}")
            
            # Determine device
            device = "cuda" if torch.cuda.is_available() and self.config.n_gpu_layers > 0 else "cpu"
            logger.info(f"Using device: {device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_path)
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_path,
                device_map="auto" if device == "cuda" else None,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            )
            
            if device == "cpu":
                self.model = self.model.to(device)
            
            self.model.eval()
            
            logger.info(f"✓ Model loaded successfully on {device}")
            
        except ImportError:
            logger.error("transformers not installed. Run: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate completion."""
        import torch
        
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")
        
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode output (remove input prompt)
        generated_text = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        
        # Apply stop sequences
        if stop:
            for stop_seq in stop:
                if stop_seq in generated_text:
                    generated_text = generated_text[:generated_text.index(stop_seq)]
        
        return generated_text
    
    def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Stream completion tokens."""
        # Transformers streaming is complex, for now just yield full response
        # TODO: Implement proper streaming with TextIteratorStreamer
        response = self.generate(prompt, max_tokens, temperature, stop)
        yield response


class LocalLLMService:
    """Service for managing local LLM inference."""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        backend: Optional[LLMBackend] = None,
        **config_kwargs
    ):
        """Initialize local LLM service.
        
        Args:
            model_path: Path to model file or HuggingFace model ID
            backend: LLM backend to use (llama_cpp, transformers, onnx)
            **config_kwargs: Additional config parameters
        """
        # Default model path from environment or use small default
        if model_path is None:
            model_path = os.getenv(
                "LOCAL_LLM_MODEL_PATH",
                "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # Small default model
            )
        
        # Auto-detect backend if not specified
        if backend is None:
            if model_path.endswith(".gguf"):
                backend = LLMBackend.LLAMA_CPP
            else:
                backend = LLMBackend.TRANSFORMERS
        
        # Create config
        self.config = LLMConfig(
            model_path=model_path,
            backend=backend,
            **config_kwargs
        )
        
        # Initialize client
        self.client: Optional[BaseLLMClient] = None
        self._init_client()
    
    def _init_client(self):
        """Initialize LLM client."""
        try:
            if self.config.backend == LLMBackend.LLAMA_CPP:
                self.client = LlamaCppClient(self.config)
            elif self.config.backend == LLMBackend.TRANSFORMERS:
                self.client = TransformersClient(self.config)
            else:
                raise ValueError(f"Unsupported backend: {self.config.backend}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate completion."""
        if not self.client:
            raise RuntimeError("LLM client not initialized")
        
        return self.client.generate(prompt, max_tokens, temperature, stop)
    
    def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> Iterator[str]:
        """Stream completion tokens."""
        if not self.client:
            raise RuntimeError("LLM client not initialized")
        
        return self.client.stream(prompt, max_tokens, temperature, stop)
    



# Singleton instance
_llm_service: Optional[LocalLLMService] = None


def get_local_llm_service(**kwargs) -> LocalLLMService:
    """Get singleton LLM service instance."""
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LocalLLMService(**kwargs)
    
    return _llm_service

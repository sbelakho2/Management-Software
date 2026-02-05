"""
Sensei OS Configuration Module

Centralized configuration management with environment variable loading,
validation, and secure secret handling.
"""

import logging
from functools import lru_cache
from typing import List, Literal

import json

from pydantic import Field, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        enable_decoding=False,
    )
    
    # Application
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=32)
    
    # API
    API_PREFIX: str = "/api/v1"
    # Local dev + Playwright E2E (Next dev server may run on 3001/3100 if 3000 is busy)
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3100"]
    
    # Database
    DATABASE_URL: str = Field(..., description="Async PostgreSQL connection string")
    DATABASE_URL_SYNC: str = Field(..., description="Sync PostgreSQL connection string")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_STATEMENT_CACHE_SIZE: int = 1000
    DATABASE_STATEMENT_TIMEOUT_MS: int = 10000
    
    # starzERP Database (MySQL)
    # SECURITY: This URL MUST be provided via environment variable in production.
    # The default value is intentionally invalid to prevent accidental use.
    STARZ_ERP_DATABASE_URL: str = Field(
        default="",
        description="MySQL connection string for starzERP (required if ERP integration enabled)"
    )
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    
    # S3-Compatible Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "sensei-files"
    S3_REGION: str = "us-east-1"
    
    # Authentication
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOTP_ISSUER: str = "SenseiOS"
    
    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    SKIP_EMAIL_VERIFICATION: bool = False  # Set to True only in development/testing
    
    # Rate Limiting
    # Enabled automatically in production; opt-in elsewhere.
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".png", ".jpg", ".jpeg", ".gif",
        ".zip", ".csv", ".txt",
    ]
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    SLOW_REQUEST_THRESHOLD_MS: int = 1000
    
    # Feature Flags
    FEATURE_PHASE_2_NPI: bool = False
    FEATURE_PHASE_3_PRODUCTION: bool = False
    FEATURE_AI_SUGGESTIONS: bool = True
    FEATURE_OFFLINE_MODE: bool = False

    # Background Workers (disabled by default)
    MUDA_NUDGING_WORKER_ENABLED: bool = False
    MUDA_NUDGING_WORKER_INTERVAL_SECONDS: int = 300
    MUDA_NUDGING_WORKER_RECIPIENT_IDS: str = ""  # comma-separated
    
    # Muda Nudging Thresholds
    MUDA_THRESHOLD_DEFECT_RATE_PCT: float = 3.0
    MUDA_THRESHOLD_OEE_PCT: float = 65.0
    MUDA_THRESHOLD_CHANGEOVER_MINUTES: float = 30.0
    MUDA_THRESHOLD_INVENTORY_DAYS: float = 5.0
    MUDA_THRESHOLD_IDLE_TIME_PCT: float = 20.0

    # AI Settings (On-Device Only)
    AI_EMBEDDING_PROVIDER: Literal["local"] = "local"
    AI_MODEL_TEXT: str = "llama-3-8b"
    AI_MODEL_EMBEDDING: str = "all-MiniLM-L6-v2"
    AI_MODEL_VLM: str = "llava-v1.6-7b"
    
    # Email Settings
    SMTP_HOST: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("[") and raw.endswith("]"):
                # Try JSON first (e.g. ["http://a", "http://b"]).
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(v).strip() for v in parsed if str(v).strip()]
                except Exception:
                    # Fall back to splitting a bracketed, non-JSON list.
                    inner = raw[1:-1]
                    return [p.strip().strip("\"'") for p in inner.split(",") if p.strip()]
            # Comma-separated string.
            return [p.strip().strip("\"'") for p in raw.split(",") if p.strip()]
        return value
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@sensei-os.com"
    SMTP_FROM_NAME: str = "Sensei OS"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    EMAIL_ENABLED: bool = False
    
    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Localization
    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: List[str] = ["en", "fr"]
    DEFAULT_TIMEZONE: str = "Africa/Casablanca"
    
    # ML/AI Model Configuration
    ML_MODEL_PATH: str = "backend/models"
    ML_USE_ONNX: bool = True  # Use ONNX runtime for embeddings (faster, CPU-optimized)
    ML_ONNX_MODEL_PATH: str = "backend/models/sensei-mfg-onnx"  # Path to quantized ONNX models
    ML_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # Fallback model
    ML_EMBEDDING_DIM: int = 384
    ML_DEVICE: str = "auto"  # auto, cpu, cuda - auto detects available hardware
    
    # Local LLM Configuration (On-Device Only)
    LOCAL_LLM_MODEL_PATH: str = "backend/models/llm/tinyllama-1.1b-chat.gguf"
    LOCAL_LLM_CONTEXT_LENGTH: int = 4096
    LOCAL_LLM_MAX_TOKENS: int = 512
    LOCAL_LLM_TEMPERATURE: float = 0.7
    LOCAL_LLM_N_GPU_LAYERS: int = 0  # 0 = CPU only
    LOCAL_LLM_N_THREADS: int = 4
    
    # VPS-Optimized Chatbot Configuration
    # These settings are tuned for CPU-only VPS deployment
    CHATBOT_ENABLED: bool = True
    CHATBOT_MODEL_PATH: str = "backend/models/llm/qwen2.5-3b-instruct-q4_k_m.gguf"
    CHATBOT_MODEL_URL: str = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
    CHATBOT_CONTEXT_LENGTH: int = 2048  # Reduced for VPS memory efficiency
    CHATBOT_MAX_TOKENS: int = 256  # Shorter responses for faster inference
    CHATBOT_TEMPERATURE: float = 0.7
    CHATBOT_N_GPU_LAYERS: int = 0  # CPU only for VPS
    CHATBOT_N_THREADS: int = 2  # Conservative for shared VPS
    CHATBOT_BATCH_SIZE: int = 256  # Smaller batch for memory efficiency
    CHATBOT_MAX_SESSIONS: int = 100  # Limit concurrent sessions
    CHATBOT_SESSION_TIMEOUT_HOURS: int = 24
    CHATBOT_RATE_LIMIT_PER_MINUTE: int = 20
    CHATBOT_INFERENCE_TIMEOUT_SECONDS: int = 30
    
    @field_validator("ML_MODEL_PATH", "ML_ONNX_MODEL_PATH")
    @classmethod
    def ensure_model_paths_exist(cls, v: str) -> str:
        """Create model directories if they don't exist."""
        from pathlib import Path
        path = Path(v)
        if not path.exists():
            logger.info(f"Creating model directory: {v}")
            path.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is sufficiently long and complex."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

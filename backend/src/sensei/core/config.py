"""
Sensei OS Configuration Module

Centralized configuration management with environment variable loading,
validation, and secure secret handling.

Security Features:
- Production secret key validation (entropy check)
- Secure cookie enforcement in production
- Email service validation
- HTTPS enforcement settings
"""

import hashlib
import logging
import re
import secrets
from functools import lru_cache
from typing import List, Literal, Optional

import json

from pydantic import Field, field_validator, model_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# Known weak/default secret keys that must be rejected in production
KNOWN_WEAK_SECRETS = {
    "development-secret-key-change-in-production",
    "your-super-secret-key-change-in-production",
    "change-me-in-production",
    "secret",
    "changeme",
    "password",
    "test_secret_key_that_is_at_least_32_chars",
    "jwt-secret-key-change-in-production",
}


def _calculate_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string to detect weak secrets."""
    if not s:
        return 0.0
    from collections import Counter
    import math
    
    counter = Counter(s)
    length = len(s)
    entropy = 0.0
    
    for count in counter.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    
    return entropy


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
    
    # Secure Cookie/Session Settings
    # These are enforced in production regardless of settings
    SECURE_COOKIES: bool = Field(
        default=False,
        description="Use secure (HTTPS-only) cookies. Auto-enabled in production."
    )
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "lax"
    SESSION_COOKIE_SECURE: bool = Field(
        default=False,
        description="Require HTTPS for session cookies. Auto-enabled in production."
    )
    
    # Session Binding (Device Fingerprinting)
    SESSION_BINDING_ENABLED: bool = Field(
        default=True,
        description="Bind sessions to device fingerprint to prevent session hijacking"
    )
    SESSION_FINGERPRINT_SALT: str = Field(
        default="",
        description="Salt for session fingerprint hashing. Auto-generated if empty."
    )
    
    # Password Breach Checking (haveibeenpwned)
    PASSWORD_BREACH_CHECK_ENABLED: bool = Field(
        default=True,
        description="Check passwords against known breached passwords (uses k-anonymity)"
    )
    PASSWORD_BREACH_CHECK_TIMEOUT_SECONDS: int = 3
    
    # HTTPS Enforcement
    FORCE_HTTPS: bool = Field(
        default=False,
        description="Redirect all HTTP requests to HTTPS. Auto-enabled in production."
    )
    HSTS_ENABLED: bool = Field(
        default=True,
        description="Enable HTTP Strict Transport Security header"
    )
    HSTS_MAX_AGE_SECONDS: int = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = False  # Requires manual submission to preload list
    
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
    
    # Observability - OpenTelemetry
    OTEL_ENABLED: bool = Field(
        default=False,
        description="Enable OpenTelemetry distributed tracing"
    )
    OTEL_SERVICE_NAME: str = "sensei-os"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="",
        description="OpenTelemetry collector endpoint (e.g., http://localhost:4317)"
    )
    OTEL_EXPORTER_OTLP_HEADERS: str = Field(
        default="",
        description="Headers for OTLP exporter (format: key=value,key2=value2)"
    )
    OTEL_TRACES_SAMPLER: Literal["always_on", "always_off", "traceidratio", "parentbased_always_on", "parentbased_traceidratio"] = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 0.1  # Sample 10% of traces by default
    
    # Prometheus Metrics
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint at /metrics"
    )
    METRICS_PATH: str = "/metrics"
    
    # SLO Configuration
    SLO_LATENCY_P99_MS: int = Field(
        default=1000,
        description="P99 latency SLO target in milliseconds"
    )
    SLO_ERROR_RATE_PCT: float = Field(
        default=0.1,
        description="Error rate SLO target as percentage (0.1 = 0.1%)"
    )
    SLO_AVAILABILITY_PCT: float = Field(
        default=99.9,
        description="Availability SLO target as percentage"
    )
    
    # Webhook/Event System
    WEBHOOKS_ENABLED: bool = Field(
        default=True,
        description="Enable outbound webhook notifications"
    )
    WEBHOOKS_MAX_RETRIES: int = 3
    WEBHOOKS_RETRY_DELAY_SECONDS: int = 60
    WEBHOOKS_TIMEOUT_SECONDS: int = 30
    WEBHOOKS_SECRET_HEADER: str = "X-Sensei-Webhook-Signature"
    
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
    EMAIL_REQUIRED_IN_PRODUCTION: bool = Field(
        default=True,
        description="Require email configuration in production. Set to False only if using alternative notification system."
    )
    EMAIL_FAIL_SILENTLY: bool = Field(
        default=False,
        description="If True, email failures are logged but don't raise exceptions. Not recommended in production."
    )
    
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
    SOCRATIC_RAG_RETRIEVAL_MODE: str = "lexical"  # lexical or onnx — retrieval strategy for Socratic pedagogy RAG
    
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

    # ── Domain Service Defaults ─────────────────────────────────────────
    # #385 production_scheduling — fallback scheduling horizon (days)
    SCHEDULING_HORIZON_DAYS: int = 365
    # #386 mrp_lite — planning horizon (days)
    MRP_PLANNING_HORIZON_DAYS: int = 30
    # #388 lot_serial_traceability — expiry warning threshold (days)
    LOT_EXPIRY_WARNING_DAYS: int = 30
    # #389 lot_serial_traceability — max genealogy trace depth
    LOT_GENEALOGY_MAX_DEPTH: int = 10
    # #390 label_printing — scan recovery workflow timeout (seconds)
    LABEL_PRINT_TIMEOUT_SECONDS: int = 300
    # #391 qms_quality — SPC lookback period (days)
    QMS_SPC_LOOKBACK_DAYS: int = 180
    # #393 various — default lookback for analytics (days)
    ANALYTICS_LOOKBACK_DAYS: int = 90
    # #394 audit_log — default query limit
    AUDIT_LOG_QUERY_LIMIT: int = 50
    # #395 wms_integration — cycle count batch size
    WMS_CYCLE_COUNT_BATCH_SIZE: int = 10
    # #397 backup_scheduler — defaults
    BACKUP_FULL_RETENTION_DAYS: int = 30
    BACKUP_INCREMENTAL_RETENTION_DAYS: int = 7
    # #398 health_checks — thresholds
    HEALTH_LATENCY_OK_MS: int = 60
    HEALTH_LATENCY_WARN_MS: int = 30
    HEALTH_CPU_OK_PCT: float = 70.0
    HEALTH_CPU_WARN_PCT: float = 30.0
    HEALTH_MEMORY_OK_PCT: float = 80.0
    HEALTH_MEMORY_WARN_PCT: float = 40.0
    # #392 lsw_scheduling — default durations for walk types (JSON map)
    LSW_DEFAULT_DURATIONS: dict[str, int] = {
        "daily-gemba": 30, "daily-tier1": 15, "daily-safety": 10,
        "weekly-tier2": 60, "weekly-coaching": 30, "weekly-process-audit": 20,
        "monthly-tier3": 120, "monthly-standard-review": 45,
        "monthly-training-check": 30, "monthly-recognition": 15,
    }
    # #396 wms_integration — cycle count priority thresholds
    WMS_CYCLE_COUNT_CRITICAL_THRESHOLD: int = 50
    WMS_CYCLE_COUNT_HIGH_THRESHOLD: int = 20

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
        """Ensure secret key is sufficiently long, complex, and not a known weak value."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        
        # Check against known weak secrets (will be validated further in model_validator for production)
        if v.lower() in KNOWN_WEAK_SECRETS or any(weak in v.lower() for weak in ["change", "default", "example", "test"]):
            # Log warning but don't fail - model_validator will handle production enforcement
            logger.warning(
                "SECRET_KEY appears to be a development/example key. "
                "This MUST be changed before production deployment."
            )
        
        return v
    
    @field_validator("SESSION_FINGERPRINT_SALT", mode="before")
    @classmethod
    def ensure_fingerprint_salt(cls, v: str) -> str:
        """Generate fingerprint salt if not provided."""
        if not v:
            return secrets.token_hex(32)
        return v
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """
        Comprehensive validation of production settings.
        
        This validator enforces security requirements that are critical
        for production deployments and cannot be bypassed.
        """
        if self.ENVIRONMENT == "production":
            # 1. Validate SECRET_KEY is not a known weak value
            secret_lower = self.SECRET_KEY.lower()
            if secret_lower in KNOWN_WEAK_SECRETS:
                raise ValueError(
                    f"SECRET_KEY is a known weak/default value. "
                    f"Generate a secure key with: openssl rand -hex 32"
                )
            
            # Check for common weak patterns
            weak_patterns = ["change", "default", "example", "test", "development", "password"]
            for pattern in weak_patterns:
                if pattern in secret_lower:
                    raise ValueError(
                        f"SECRET_KEY contains '{pattern}' which suggests a non-production key. "
                        f"Generate a secure key with: openssl rand -hex 32"
                    )
            
            # Check entropy (a good random key should have entropy > 4.0)
            entropy = _calculate_entropy(self.SECRET_KEY)
            if entropy < 3.5:
                raise ValueError(
                    f"SECRET_KEY has low entropy ({entropy:.2f}), suggesting a weak key. "
                    f"Generate a secure key with: openssl rand -hex 32"
                )
            
            # 2. Force secure cookie settings in production
            object.__setattr__(self, "SECURE_COOKIES", True)
            object.__setattr__(self, "SESSION_COOKIE_SECURE", True)
            object.__setattr__(self, "FORCE_HTTPS", True)
            
            # 3. Validate email configuration if required
            if self.EMAIL_REQUIRED_IN_PRODUCTION and not self.EMAIL_ENABLED:
                logger.warning(
                    "EMAIL_ENABLED is False in production. Password reset and email verification "
                    "will not work. Set EMAIL_REQUIRED_IN_PRODUCTION=False to suppress this warning "
                    "if using an alternative notification system."
                )
            
            if self.EMAIL_ENABLED and not self.SMTP_HOST:
                raise ValueError(
                    "EMAIL_ENABLED is True but SMTP_HOST is not configured. "
                    "Provide SMTP settings or disable email."
                )
            
            # 4. Ensure DEBUG is disabled
            if self.DEBUG:
                logger.warning(
                    "DEBUG=True in production. This may expose sensitive information. "
                    "Setting DEBUG=False for safety."
                )
                object.__setattr__(self, "DEBUG", False)
            
            # 5. Validate CORS origins don't include localhost
            localhost_origins = [o for o in self.CORS_ORIGINS if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                logger.warning(
                    f"CORS_ORIGINS contains localhost entries in production: {localhost_origins}. "
                    f"This is likely a configuration error."
                )
            
            # 6. Ensure rate limiting is enabled
            if not self.RATE_LIMIT_ENABLED:
                logger.info("Enabling rate limiting for production environment")
                object.__setattr__(self, "RATE_LIMIT_ENABLED", True)
            
            # 7. Validate frontend URL is HTTPS
            if self.FRONTEND_URL.startswith("http://"):
                logger.warning(
                    f"FRONTEND_URL uses HTTP ({self.FRONTEND_URL}) in production. "
                    f"This should be HTTPS for security."
                )
        
        elif self.ENVIRONMENT == "staging":
            # Staging should also enforce some security settings
            object.__setattr__(self, "SECURE_COOKIES", True)
            object.__setattr__(self, "SESSION_COOKIE_SECURE", True)
        
        return self
    
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

"""
Sensei OS Configuration Module

Centralized configuration management with environment variable loading,
validation, and secure secret handling.
"""

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=32)
    
    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = Field(..., description="Async PostgreSQL connection string")
    DATABASE_URL_SYNC: str = Field(..., description="Sync PostgreSQL connection string")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    
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
    
    # Rate Limiting
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

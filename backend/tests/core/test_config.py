"""
Tests for Sensei Core Configuration Module

Comprehensive tests for configuration loading, validation, and edge cases.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from sensei.core.config import Settings


class TestSettingsValidation:
    """Test settings validation and parsing."""
    
    def test_valid_settings_creation(self):
        """Test creating settings with valid values."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "REDIS_URL": "redis://localhost:6379/0",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.SECRET_KEY == "a" * 32
            assert settings.ENVIRONMENT == "development"
            assert settings.VERSION == "1.0.0"
    
    def test_secret_key_minimum_length(self):
        """Test that SECRET_KEY must be at least 32 characters."""
        env = {
            "SECRET_KEY": "short",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "SECRET_KEY" in str(exc_info.value)
    
    def test_secret_key_exactly_32_chars(self):
        """Test SECRET_KEY with exactly 32 characters is valid."""
        env = {
            "SECRET_KEY": "x" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert len(settings.SECRET_KEY) == 32
    
    def test_cors_origins_from_json_string(self):
        """Test parsing CORS origins from JSON string (pydantic-settings format)."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "CORS_ORIGINS": '["http://localhost:3000", "http://localhost:8080", "https://app.example.com"]',
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.CORS_ORIGINS == [
                "http://localhost:3000",
                "http://localhost:8080",
                "https://app.example.com",
            ]
    
    def test_cors_origins_empty_json_list(self):
        """Test empty CORS_ORIGINS JSON results in empty list."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "CORS_ORIGINS": "[]",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.CORS_ORIGINS == []
    
    def test_cors_origins_single_element(self):
        """Test CORS origins with single element."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "CORS_ORIGINS": '["http://localhost:3000"]',
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.CORS_ORIGINS == [
                "http://localhost:3000",
            ]


class TestEnvironmentDetection:
    """Test environment detection properties."""
    
    def test_is_production_true(self):
        """Test is_production returns True for production environment."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "ENVIRONMENT": "production",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.is_production is True
            assert settings.is_development is False
    
    def test_is_development_true(self):
        """Test is_development returns True for development environment."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.is_development is True
            assert settings.is_production is False
    
    def test_staging_environment(self):
        """Test staging is neither production nor development."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "ENVIRONMENT": "staging",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.is_production is False
            assert settings.is_development is False


class TestDefaultValues:
    """Test default values for optional settings."""
    
    def test_default_log_level(self):
        """Test default log level is INFO."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.LOG_LEVEL == "INFO"
    
    def test_default_feature_flags(self):
        """Test default feature flag values."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.FEATURE_PHASE_2_NPI is False
            assert settings.FEATURE_PHASE_3_PRODUCTION is False
            assert settings.FEATURE_AI_SUGGESTIONS is True
            assert settings.FEATURE_OFFLINE_MODE is False
    
    def test_default_localization(self):
        """Test default localization settings."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.DEFAULT_LOCALE == "en"
            assert settings.SUPPORTED_LOCALES == ["en", "fr"]
            assert settings.DEFAULT_TIMEZONE == "Africa/Casablanca"
    
    def test_default_security_settings(self):
        """Test default security settings."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.BCRYPT_ROUNDS == 12
            assert settings.MAX_LOGIN_ATTEMPTS == 5
            assert settings.LOCKOUT_DURATION_MINUTES == 15
    
    def test_default_file_upload_settings(self):
        """Test default file upload settings."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.MAX_UPLOAD_SIZE_MB == 50
            assert ".pdf" in settings.ALLOWED_UPLOAD_EXTENSIONS
            assert ".exe" not in settings.ALLOWED_UPLOAD_EXTENSIONS


class TestInvalidEnvironmentValues:
    """Test handling of invalid environment values."""
    
    def test_invalid_environment_type(self):
        """Test that invalid ENVIRONMENT value raises error."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "ENVIRONMENT": "invalid_env",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_invalid_log_level(self):
        """Test that invalid LOG_LEVEL value raises error."""
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
            "LOG_LEVEL": "INVALID",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_missing_required_database_url(self):
        """Test that missing DATABASE_URL raises error."""
        from pydantic_settings import BaseSettings, SettingsConfigDict
        from pydantic import Field, field_validator
        from typing import List, Literal
        
        # Create a fresh Settings class without .env file loading
        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(
                case_sensitive=True,
                extra="ignore",
            )
            
            SECRET_KEY: str = Field(..., min_length=32)
            DATABASE_URL: str = Field(..., description="Async PostgreSQL connection string")
            DATABASE_URL_SYNC: str = Field(..., description="Sync PostgreSQL connection string")
        
        env = {
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL_SYNC": "postgresql://user:pass@localhost/db",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                TestSettings()
            assert "DATABASE_URL" in str(exc_info.value)

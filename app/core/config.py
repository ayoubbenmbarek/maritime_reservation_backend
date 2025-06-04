"""
Core configuration module for the Maritime Reservation System.
Handles environment variables, database settings, and application configuration.
"""

from typing import List, Optional, Union
from pydantic import BaseSettings, validator, AnyHttpUrl
import secrets
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Basic application settings
    PROJECT_NAME: str = "Maritime Reservation System"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Comprehensive ferry booking and reservation platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "maritime_user"
    POSTGRES_PASSWORD: str = "maritime_password"
    POSTGRES_DB: str = "maritime_reservation"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return (
            f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:"
            f"{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get('REDIS_PASSWORD') else ""
        return (
            f"redis://{password_part}{values.get('REDIS_HOST')}:"
            f"{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
        )
    
    # Email settings
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    @validator("EMAILS_FROM_NAME")
    def get_project_name(cls, v: Optional[str], values: dict) -> str:
        if not v:
            return values["PROJECT_NAME"]
        return v
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # External API settings
    FERRY_API_TIMEOUT: int = 30
    FERRY_API_RETRY_ATTEMPTS: int = 3
    FERRY_API_RATE_LIMIT: int = 100  # requests per minute
    
    # CTN (Compagnie Tunisienne de Navigation) API
    CTN_API_BASE_URL: Optional[str] = None
    CTN_API_KEY: Optional[str] = None
    CTN_API_SECRET: Optional[str] = None
    
    # GNV (Grandi Navi Veloci) API
    GNV_API_BASE_URL: Optional[str] = None
    GNV_API_KEY: Optional[str] = None
    GNV_API_SECRET: Optional[str] = None
    
    # Corsica Lines API
    CORSICA_API_BASE_URL: Optional[str] = None
    CORSICA_API_KEY: Optional[str] = None
    CORSICA_API_SECRET: Optional[str] = None
    
    # Payment gateway settings
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_ENVIRONMENT: str = "sandbox"  # sandbox or live
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]
    UPLOAD_DIRECTORY: str = "uploads"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Cache settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Internationalization settings
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: List[str] = ["en", "fr", "ar", "it"]
    DEFAULT_CURRENCY: str = "EUR"
    SUPPORTED_CURRENCIES: List[str] = ["EUR", "TND", "USD"]
    
    # Business logic settings
    BOOKING_EXPIRY_MINUTES: int = 30
    MAX_PASSENGERS_PER_BOOKING: int = 20
    MAX_VEHICLES_PER_BOOKING: int = 5
    COMMISSION_RATE: float = 0.05  # 5%
    
    # Monitoring and observability
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Development settings
    DEBUG: bool = False
    TESTING: bool = False
    
    @validator("DEBUG", pre=True)
    def set_debug_mode(cls, v: bool, values: dict) -> bool:
        return values.get("ENVIRONMENT") == "development"
    
    # Health check settings
    HEALTH_CHECK_TIMEOUT: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()


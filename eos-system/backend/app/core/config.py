"""
EOS System — Core Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # General
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    PROJECT_NAME: str = "EOS System"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Database (no hardcoded passwords)
    DATABASE_URL: str  # Required: set in .env
    DATABASE_TEST_URL: str  # Required: set in .env
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # Security (no hardcoded secrets)
    SECRET_KEY: str  # Required: set in .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # Tenant
    DEFAULT_TENANT_SCHEMA: str = "public"
    TENANT_HEADER: str = "X-Tenant-ID"
    
    # AI
    OPENAI_API_KEY: Optional[str] = None
    HUGGINGFACE_MODEL: str = "aubmindlab/bert-base-arabic-cased"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    
    # Egyptian Compliance
    ETA_API_URL: str = "https://api.eta.gov.eg"
    ETA_API_KEY: Optional[str] = None
    NOSI_API_URL: str = "https://api.nosi.gov.eg"
    NOSI_API_KEY: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()


settings = get_settings()

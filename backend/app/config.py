from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "2TO EOS"
    app_version: str = "0.3.0"
    app_env: str = "development"
    app_start_time: float = Field(default_factory=lambda: __import__('time').time())
    database_url: str = "sqlite+pysqlite:///:memory:"
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "development-only-secret"
    access_token_ttl_seconds: int = Field(default=3600, ge=300, le=86400)
    refresh_token_ttl_seconds: int = Field(default=2592000, ge=86400, le=7776000)
    rate_limit_auth_per_minute: int = Field(default=120, ge=1, le=10000)
    max_request_body_bytes: int = Field(default=1048576, ge=1024, le=104857600)
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # SSO
    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    okta_client_id: str = ""
    okta_client_secret: str = ""
    okta_domain: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # Email (SendGrid)
    sendgrid_api_key: str = ""
    email_from_address: str = "noreply@2to-eos.com"
    email_from_name: str = "2TO EOS"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str, info) -> str:
        env = info.data.get("app_env", "development")
        placeholder_hints = ("development-only-secret", "change-me", "change-this", "changeme")
        lowered = value.lower()
        if env == "production" and (
            value == "development-only-secret"
            or len(value) < 32
            or any(hint in lowered for hint in placeholder_hints)
        ):
            raise ValueError("JWT_SECRET must be a unique 32+ character secret in production")
        if not value:
            raise ValueError("JWT_SECRET cannot be empty")
        return value

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        valid_envs = {"development", "staging", "production", "test"}
        if value not in valid_envs:
            raise ValueError(f"APP_ENV must be one of: {', '.join(valid_envs)}")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL cannot be empty")
        try:
            parsed = urlparse(value)
            scheme = parsed.scheme.split("+")[0] if "+" in parsed.scheme else parsed.scheme
            if scheme not in ("sqlite", "postgresql", "mysql"):
                raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        except Exception as e:
            raise ValueError(f"Invalid DATABASE_URL format: {e}") from e
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if not value:
            raise ValueError("REDIS_URL cannot be empty")
        try:
            parsed = urlparse(value)
            if parsed.scheme not in ("redis", "rediss"):
                raise ValueError(f"Invalid Redis URL scheme: {parsed.scheme}")
        except Exception as e:
            raise ValueError(f"Invalid REDIS_URL format: {e}") from e
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        if not value:
            raise ValueError("CORS_ORIGINS cannot be empty")
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        for origin in origins:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid CORS origin format: {origin}")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

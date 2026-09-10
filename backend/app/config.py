from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "2TO EOS"
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:///:memory:"
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "development-only-secret"
    access_token_ttl_seconds: int = Field(default=3600, ge=300, le=86400)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str, info) -> str:
        env = info.data.get("app_env", "development")
        if env == "production" and (value == "development-only-secret" or len(value) < 32):
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        if not value:
            raise ValueError("JWT_SECRET cannot be empty")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


class ApiError(BaseModel):
    detail: str


@lru_cache
def get_settings() -> Settings:
    return Settings()

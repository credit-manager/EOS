from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "2TO EOS"
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:///:memory:"
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "development-only-secret"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

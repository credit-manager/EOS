from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings for the v2 application boundary."""

    app_name: str = "EOS Dynamic Business Platform"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = ""
    secret_key: str = ""
    max_body_bytes: int = 10 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("EOS_ENV", "development").strip().lower(),
            database_url=os.getenv("DATABASE_URL", "").strip(),
            secret_key=os.getenv("EOS_SECRET_KEY", "").strip(),
            max_body_bytes=int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024))),
        )

    def validate(self) -> None:
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("EOS_ENV must be development, test, staging, or production")
        if self.max_body_bytes <= 0:
            raise ValueError("EOS_MAX_BODY_BYTES must be positive")
        if self.environment in {"staging", "production"} and not self.database_url:
            raise ValueError("DATABASE_URL is required outside development/test")
        if self.environment == "production" and len(self.secret_key) < 32:
            raise ValueError("EOS_SECRET_KEY must contain at least 32 characters in production")

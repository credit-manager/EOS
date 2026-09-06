from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _csv_env(name: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings for the v2 application boundary."""

    app_name: str = "EOS Dynamic Business Platform"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = ""
    secret_key: str = ""
    max_body_bytes: int = 10 * 1024 * 1024
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = 30.0
    allowed_hosts: tuple[str, ...] = ()
    cors_origins: tuple[str, ...] = ()
    metrics_token: str = ""
    auth_mode: str = "hs256"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("EOS_ENV", "development").strip().lower(),
            database_url=os.getenv("DATABASE_URL", "").strip(),
            secret_key=os.getenv("EOS_SECRET_KEY", "").strip(),
            max_body_bytes=int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024))),
            ai_base_url=os.getenv("EOS_AI_BASE_URL", "").strip(),
            ai_api_key=os.getenv("EOS_AI_API_KEY", "").strip(),
            ai_model=os.getenv("EOS_AI_MODEL", "").strip(),
            ai_timeout_seconds=float(os.getenv("EOS_AI_TIMEOUT_SECONDS", "30")),
            allowed_hosts=_csv_env("EOS_ALLOWED_HOSTS"),
            cors_origins=_csv_env("EOS_CORS_ORIGINS"),
            metrics_token=os.getenv("EOS_METRICS_TOKEN", "").strip(),
            auth_mode=os.getenv("EOS_AUTH_MODE", "hs256").strip().lower(),
            oidc_issuer=os.getenv("EOS_OIDC_ISSUER", "").strip(),
            oidc_audience=os.getenv("EOS_OIDC_AUDIENCE", "").strip(),
            oidc_jwks_url=os.getenv("EOS_OIDC_JWKS_URL", "").strip(),
        )

    def validate(self) -> None:
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("EOS_ENV must be development, test, staging, or production")
        if self.auth_mode not in {"hs256", "oidc"}:
            raise ValueError("EOS_AUTH_MODE must be hs256 or oidc")
        if self.max_body_bytes <= 0:
            raise ValueError("EOS_MAX_BODY_BYTES must be positive")
        if self.ai_timeout_seconds <= 0 or self.ai_timeout_seconds > 120:
            raise ValueError("EOS_AI_TIMEOUT_SECONDS must be between 0 and 120")
        if self.environment in {"staging", "production"} and not self.database_url:
            raise ValueError("DATABASE_URL is required outside development/test")
        if self.environment == "production" and self.auth_mode != "oidc":
            raise ValueError("EOS_AUTH_MODE must be oidc in production")
        if self.environment == "production" and len(self.secret_key) < 32 and self.auth_mode == "hs256":
            raise ValueError("EOS_SECRET_KEY must contain at least 32 characters in production")
        if any((self.ai_base_url, self.ai_api_key, self.ai_model)) and not all((self.ai_base_url, self.ai_api_key, self.ai_model)):
            raise ValueError("AI Composer configuration requires EOS_AI_BASE_URL, EOS_AI_API_KEY, and EOS_AI_MODEL together")
        if self.environment == "production" and not self.allowed_hosts:
            raise ValueError("EOS_ALLOWED_HOSTS is required in production")
        if self.environment == "production" and not self.cors_origins:
            raise ValueError("EOS_CORS_ORIGINS is required in production")
        if self.environment == "production" and len(self.metrics_token) < 16:
            raise ValueError("EOS_METRICS_TOKEN must contain at least 16 characters in production")
        if self.auth_mode == "oidc":
            if not all((self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url)):
                raise ValueError("OIDC authentication requires EOS_OIDC_ISSUER, EOS_OIDC_AUDIENCE, and EOS_OIDC_JWKS_URL")
            for name, value in (("EOS_OIDC_ISSUER", self.oidc_issuer), ("EOS_OIDC_JWKS_URL", self.oidc_jwks_url)):
                scheme = urlparse(value).scheme.lower()
                if self.environment == "production" and scheme != "https":
                    raise ValueError(f"{name} must use HTTPS in production")

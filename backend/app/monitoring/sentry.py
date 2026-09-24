"""Sentry integration for error monitoring."""
import os
import logging

logger = logging.getLogger("2to-eos.monitoring.sentry")

def init_sentry() -> None:
    """Initialize Sentry if DSN is configured."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry DSN not configured, error monitoring disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", "development"),
            release=os.getenv("APP_VERSION", "1.0.0"),
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("Sentry initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed, run: pip install sentry-sdk")
    except Exception as e:
        logger.error("Failed to initialize Sentry: %s", e)

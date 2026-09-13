import logging

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from .config import get_settings

logger = logging.getLogger("2to-eos.redis")

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=2.0,
            retry_on_timeout=False,
            retry=Retry(NoBackoff(), retries=1),
            health_check_interval=30,
        )
    return _redis_client


def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception as exc:
            logger.warning("Error closing Redis connection: %s", exc)
        finally:
            _redis_client = None


def check_redis_health() -> bool:
    try:
        r = get_redis()
        r.ping()
        return True
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return False

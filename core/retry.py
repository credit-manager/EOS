"""
RETRY WITH EXPONENTIAL BACKOFF
==============================
General-purpose retry decorator for transient failures.
"""
import time
import logging
import asyncio
import random
from typing import Callable, Type, Optional, Tuple
from functools import wraps

logger = logging.getLogger("eos.retry")


class RetryExhaustedError(Exception):
    """All retry attempts have been exhausted."""

    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {type(last_exception).__name__}"
        )


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    base_delay: float = 0.5,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """Retry transient operations with capped exponential backoff and jitter."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("delay values must be >= 0")
    if backoff_factor < 1:
        raise ValueError("backoff_factor must be >= 1")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:
                    last_error = exc
                    if attempt >= max_attempts - 1:
                        break
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    delay = max(0.0, delay + delay * 0.1 * random.uniform(-1, 1))
                    logger.warning(
                        "%s attempt %d/%d failed (%s); retrying in %.2fs",
                        func.__name__, attempt + 1, max_attempts, type(exc).__name__, delay,
                    )
                    if on_retry:
                        try:
                            on_retry(attempt + 1, exc)
                        except Exception:
                            logger.exception("retry callback failed")
                    await asyncio.sleep(delay)
            raise RetryExhaustedError(last_error or RuntimeError("unknown retry failure"), max_attempts)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    last_error = exc
                    if attempt >= max_attempts - 1:
                        break
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    delay = max(0.0, delay + delay * 0.1 * random.uniform(-1, 1))
                    logger.warning(
                        "%s attempt %d/%d failed (%s); retrying in %.2fs",
                        func.__name__, attempt + 1, max_attempts, type(exc).__name__, delay,
                    )
                    if on_retry:
                        try:
                            on_retry(attempt + 1, exc)
                        except Exception:
                            logger.exception("retry callback failed")
                    time.sleep(delay)
            raise RetryExhaustedError(last_error or RuntimeError("unknown retry failure"), max_attempts)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

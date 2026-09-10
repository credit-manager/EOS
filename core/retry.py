"""
RETRY WITH EXPONENTIAL BACKOFF
==============================
General-purpose retry decorator for transient failures.

Usage:
    @retry(max_attempts=3, backoff_factor=2, retry_on=(ConnectionError, TimeoutError))
    async def call_external_service():
        ...

    # Or as a context manager:
    async with RetryContext(max_attempts=3) as retry_ctx:
        result = await call_external_service()
        retry_ctx.record_success()
"""
import time
import logging
import asyncio
from typing import Callable, Type, Optional, Tuple, Any
from functools import wraps

logger = logging.getLogger("eos.retry")


class RetryExhaustedError(Exception):
    """All retry attempts have been exhausted."""

    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )


class RetryContext:
    """Context manager for manual retry control."""

    def __init__(self, max_attempts: int = 3, backoff_factor: float = 2.0,
                 base_delay: float = 0.5, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self._last_error: Optional[Exception] = None

    def record_success(self):
        self.attempt = self.max_attempts

    def record_failure(self, error: Exception):
        self._last_error = error

    def should_retry(self) -> bool:
        return self.attempt < self.max_attempts

    def wait_time(self) -> float:
        delay = min(self.base_delay * (self.backoff_factor ** self.attempt), self.max_delay)
        jitter = delay * 0.1
        import random
        return delay + random.uniform(-jitter, jitter)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._last_error = exc_val
            if self.should_retry():
                delay = self.wait_time()
                logger.warning(
                    f"Attempt {self.attempt + 1}/{self.max_attempts} failed "
                    f"({type(exc_val).__name__}), retrying in {delay:.2f}s"
                )
                self.attempt += 1
                time.sleep(delay)
                return True
            else:
                raise RetryExhaustedError(exc_val, self.max_attempts)
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._last_error = exc_val
            if self.should_retry():
                delay = self.wait_time()
                logger.warning(
                    f"Attempt {self.attempt + 1}/{self.max_attempts} failed "
                    f"({type(exc_val).__name__}), retrying in {delay:.2f}s"
                )
                self.attempt += 1
                await asyncio.sleep(delay)
                return True
            else:
                raise RetryExhaustedError(exc_val, self.attempts)
        return False


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    base_delay: float = 0.5,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """Decorator for automatic retry with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        import random
                        delay += delay * 0.1 * random.uniform(-1, 1)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_attempts} failed "
                            f"({type(e).__name__}), retrying in {delay:.2f}s"
                        )
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception:
                                pass
                        await asyncio.sleep(delay)
            raise RetryExhaustedError(last_error, max_attempts)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        import random
                        delay += delay * 0.1 * random.uniform(-1, 1)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_attempts} failed "
                            f"({type(e).__name__}), retrying in {delay:.2f}s"
                        )
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception:
                                pass
                        time.sleep(delay)
            raise RetryExhaustedError(last_error, max_attempts)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

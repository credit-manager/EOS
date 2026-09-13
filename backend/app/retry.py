import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger("2to-eos.retry")


class RetryExhaustedError(Exception):
    def __init__(self, message: str, last_exception: Exception):
        super().__init__(message)
        self.last_exception = last_exception


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def calculate_delay(config: RetryConfig, attempt: int) -> float:
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        delay = delay * (0.5 + random.random())
    
    return delay


def retry(
    config: RetryConfig | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
):
    if config is None:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            retryable_exceptions=retryable_exceptions,
        )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    
                    if attempt == config.max_retries:
                        logger.error(
                            "Retry exhausted for %s after %d attempts. Last error: %s",
                            func.__name__,
                            config.max_retries + 1,
                            str(exc),
                        )
                        raise RetryExhaustedError(
                            f"Retry exhausted for {func.__name__}",
                            last_exception=exc,
                        )
                    
                    delay = calculate_delay(config, attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.2f seconds...",
                        attempt + 1,
                        config.max_retries + 1,
                        func.__name__,
                        str(exc),
                        delay,
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    
                    if attempt == config.max_retries:
                        logger.error(
                            "Retry exhausted for %s after %d attempts. Last error: %s",
                            func.__name__,
                            config.max_retries + 1,
                            str(exc),
                        )
                        raise RetryExhaustedError(
                            f"Retry exhausted for {func.__name__}",
                            last_exception=exc,
                        )
                    
                    delay = calculate_delay(config, attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.2f seconds...",
                        attempt + 1,
                        config.max_retries + 1,
                        func.__name__,
                        str(exc),
                        delay,
                    )
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_retry(
    func: Callable,
    config: RetryConfig | None = None,
    *args,
    **kwargs,
) -> Any:
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(func(*args, **kwargs))
            else:
                return func(*args, **kwargs)
        except config.retryable_exceptions as exc:
            last_exception = exc
            
            if attempt == config.max_retries:
                raise RetryExhaustedError(
                    f"Retry exhausted for {func.__name__}",
                    last_exception=exc,
                )
            
            delay = calculate_delay(config, attempt)
            logger.warning(
                "Attempt %d/%d failed. Retrying in %.2f seconds...",
                attempt + 1,
                config.max_retries + 1,
                delay,
            )
            
            import time
            time.sleep(delay)
    
    raise last_exception

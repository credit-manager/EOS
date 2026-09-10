"""
CIRCUIT BREAKER
===============
Simple circuit breaker pattern for external service calls.

States:
  CLOSED   → Normal operation. Failures are counted.
  OPEN     → Calls are rejected immediately. After reset_timeout, moves to HALF_OPEN.
  HALF_OPEN → One trial call is allowed. Success → CLOSED, failure → OPEN.
"""
import time
import logging
from enum import Enum
from contextlib import contextmanager
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger("eos.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and calls are rejected."""

    def __init__(self, name: str, reset_at: float):
        self.name = name
        self.reset_at = reset_at
        wait = max(0, reset_at - time.time())
        super().__init__(f"Circuit breaker '{name}' is open. Retry in {wait:.1f}s")


class CircuitBreaker:
    """Thread-safe circuit breaker for protecting external service calls."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        half_open_max: int = 1,
        on_state_change: Optional[Callable] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0
        self._on_state_change = on_state_change

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _transition_to(self, new_state: CircuitState):
        old = self._state
        self._state = new_state
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.OPEN:
            self._half_open_calls = 0
        logger.info("Circuit breaker %r: %s -> %s", self.name, old.value, new_state.value)
        if self._on_state_change:
            try:
                self._on_state_change(old, new_state)
            except Exception:
                logger.exception("Circuit breaker state callback failed")

    def record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    @contextmanager
    def guard(self):
        current = self.state
        if current == CircuitState.OPEN:
            raise CircuitBreakerOpenError(self.name, self._last_failure_time + self.reset_timeout)
        if current == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max:
                raise CircuitBreakerOpenError(self.name, self._last_failure_time + self.reset_timeout)
            self._half_open_calls += 1
        try:
            yield
        except CircuitBreakerOpenError:
            raise
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with self.guard():
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with self.guard():
                return func(*args, **kwargs)

        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
            "last_failure_time": self._last_failure_time,
        }


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    reset_timeout: float = 30.0,
) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            reset_timeout=reset_timeout,
        )
    return _breakers[name]

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger("2to-eos.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    expected_exceptions: tuple = (Exception,)
    
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    last_state_change: float = field(default=time.time(), init=False)
    
    def _should_attempt_reset(self) -> bool:
        if self.state != CircuitState.OPEN:
            return False
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(
                    "Circuit breaker '%s' transitioning from HALF_OPEN to CLOSED",
                    self.name,
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(
                "Circuit breaker '%s' transitioning from HALF_OPEN to OPEN",
                self.name,
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit breaker '%s' transitioning from CLOSED to OPEN (failures: %d)",
                self.name,
                self.failure_count,
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "Circuit breaker '%s' attempting reset (transitioning to HALF_OPEN)",
                    self.name,
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.last_state_change = time.time()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def get_state_info(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
        }


class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        expected_exceptions: tuple = (Exception,),
    ) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                expected_exceptions=expected_exceptions,
            )
        return self._breakers[name]
    
    def get_all_states(self) -> dict:
        return {
            name: breaker.get_state_info()
            for name, breaker in self._breakers.items()
        }


registry = CircuitBreakerRegistry()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 3,
):
    def decorator(func: Callable) -> Callable:
        breaker = registry.get_or_create(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if not breaker.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{name}' is OPEN. Service unavailable."
                )
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except breaker.expected_exceptions:
                breaker.record_failure()
                raise
        
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator


class CircuitBreakerOpenError(Exception):
    pass

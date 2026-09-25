import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .circuit_breaker import registry as circuit_breaker_registry
from .retry import RetryConfig

logger = logging.getLogger("2to-eos.external_services")


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    name: str
    status: ServiceStatus
    response_time_ms: float
    last_check: float
    error: str | None = None
    consecutive_failures: int = 0


class ExternalServiceClient:
    def __init__(
        self,
        name: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        circuit_breaker_name: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.circuit_breaker_name = circuit_breaker_name or name
        self.retry_config = retry_config or RetryConfig(
            max_retries=3,
            base_delay=1.0,
            retryable_exceptions=(ConnectionError, TimeoutError),
        )
        
        self.health = ServiceHealth(
            name=name,
            status=ServiceStatus.UNKNOWN,
            response_time_ms=0,
            last_check=time.time(),
        )
        
        self._circuit_breaker = circuit_breaker_registry.get_or_create(
            name=self.circuit_breaker_name,
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3,
        )
    
    def _update_health(self, success: bool, response_time_ms: float, error: str | None = None) -> None:
        self.health.response_time_ms = response_time_ms
        self.health.last_check = time.time()
        
        if success:
            self.health.status = ServiceStatus.HEALTHY
            self.health.consecutive_failures = 0
            self.health.error = None
        else:
            self.health.consecutive_failures += 1
            self.health.error = error
            
            if self.health.consecutive_failures >= 5:
                self.health.status = ServiceStatus.UNHEALTHY
            elif self.health.consecutive_failures >= 2:
                self.health.status = ServiceStatus.DEGRADED
            else:
                self.health.status = ServiceStatus.UNKNOWN
    
    def can_execute(self) -> bool:
        return self._circuit_breaker.can_execute()
    
    def get_health(self) -> dict:
        return {
            "name": self.health.name,
            "status": self.health.status.value,
            "response_time_ms": self.health.response_time_ms,
            "last_check": self.health.last_check,
            "error": self.health.error,
            "consecutive_failures": self.health.consecutive_failures,
            "circuit_breaker": self._circuit_breaker.get_state_info(),
        }


class ExternalServiceRegistry:
    def __init__(self):
        self._clients: dict[str, ExternalServiceClient] = {}
    
    def register(
        self,
        name: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        circuit_breaker_name: str | None = None,
        retry_config: RetryConfig | None = None,
    ) -> ExternalServiceClient:
        client = ExternalServiceClient(
            name=name,
            base_url=base_url,
            timeout=timeout,
            circuit_breaker_name=circuit_breaker_name,
            retry_config=retry_config,
        )
        self._clients[name] = client
        return client
    
    def get(self, name: str) -> ExternalServiceClient | None:
        return self._clients.get(name)
    
    def get_all_health(self) -> dict:
        return {
            name: client.get_health()
            for name, client in self._clients.items()
        }


registry = ExternalServiceRegistry()


def external_service_call(
    service_name: str,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    client = registry.get(service_name)
    if not client:
        logger.warning("External service '%s' not registered", service_name)
        return func(*args, **kwargs)
    
    if not client.can_execute():
        raise ConnectionError(f"Service '{service_name}' is unavailable (circuit breaker open)")
    
    start_time = time.monotonic()
    try:
        result = func(*args, **kwargs)
        duration_ms = (time.monotonic() - start_time) * 1000
        client._update_health(True, duration_ms)
        return result
    except Exception as exc:
        duration_ms = (time.monotonic() - start_time) * 1000
        client._update_health(False, duration_ms, str(exc))
        raise

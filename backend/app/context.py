import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("2to-eos.context")

request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
start_time_var: ContextVar[float] = ContextVar("start_time", default=0.0)


@dataclass
class RequestContext:
    request_id: str
    user_id: str | None = None
    tenant_id: str | None = None
    client_ip: str | None = None
    start_time: float = 0.0
    path: str | None = None
    method: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "client_ip": self.client_ip,
            "start_time": self.start_time,
            "path": self.path,
            "method": self.method,
        }


def get_request_id() -> str:
    return request_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


def get_tenant_id() -> str | None:
    return tenant_id_var.get()


def get_client_ip() -> str | None:
    return client_ip_var.get()


def get_start_time() -> float:
    return start_time_var.get()


def get_request_context() -> RequestContext:
    return RequestContext(
        request_id=get_request_id(),
        user_id=get_user_id(),
        tenant_id=get_tenant_id(),
        client_ip=get_client_ip(),
        start_time=get_start_time(),
    )


def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    tenant_id: str | None = None,
    client_ip: str | None = None,
    start_time: float | None = None,
) -> None:
    if request_id is not None:
        request_id_var.set(request_id)
    if user_id is not None:
        user_id_var.set(user_id)
    if tenant_id is not None:
        tenant_id_var.set(tenant_id)
    if client_ip is not None:
        client_ip_var.set(client_ip)
    if start_time is not None:
        start_time_var.set(start_time)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())[:8]
        client_ip = request.client.host if request.client else "unknown"
        
        set_request_context(
            request_id=request_id,
            client_ip=client_ip,
            start_time=time.time(),
        )
        
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        
        response = await call_next(request)
        
        response.headers["X-Request-ID"] = request_id
        
        return response

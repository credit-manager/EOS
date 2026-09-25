import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("2to-eos.request")


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        
        request_body = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body:
                    try:
                        request_body = json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = f"<binary data: {len(body)} bytes>"
            except Exception:
                request_body = "<unable to read body>"
        
        start_time = time.monotonic()
        
        response = await call_next(request)
        
        duration_ms = (time.monotonic() - start_time) * 1000
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
        
        if request_body and not request.url.path.endswith("/token") and not request.url.path.endswith("/register"):
            log_data["request_body"] = request_body
        
        if response.status_code >= 400:
            logger.warning("Request completed with error: %s", json.dumps(log_data))
        elif duration_ms > 1000:
            logger.warning("Slow request: %s", json.dumps(log_data))
        else:
            logger.info("Request completed: %s", json.dumps(log_data))
        
        return response

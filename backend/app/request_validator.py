import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("2to-eos.validation")


class RequestValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.max_path_length = 2048
        self.max_query_length = 8192
        self.blocked_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"union\s+all\s+select",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from",
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.blocked_patterns]

    def _validate_path(self, path: str) -> tuple[bool, str]:
        if len(path) > self.max_path_length:
            return False, f"Path too long (max {self.max_path_length} characters)"
        
        for pattern in self.compiled_patterns:
            if pattern.search(path):
                return False, "Potentially malicious path detected"
        
        return True, ""

    def _validate_query(self, query: str) -> tuple[bool, str]:
        if len(query) > self.max_query_length:
            return False, f"Query string too long (max {self.max_query_length} characters)"
        
        for pattern in self.compiled_patterns:
            if pattern.search(query):
                return False, "Potentially malicious query detected"
        
        return True, ""

    def _validate_headers(self, headers: dict) -> tuple[bool, str]:
        for key, value in headers.items():
            if len(key) > 256:
                return False, f"Header key too long: {key}"
            if len(value) > 8192:
                return False, f"Header value too long: {key}"
        
        return True, ""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if path in ("/api/v1/health", "/api/v1/version", "/api/v1/ready"):
            return await call_next(request)
        
        valid, error_msg = self._validate_path(path)
        if not valid:
            logger.warning("Invalid path: %s - %s", path, error_msg)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": error_msg,
                    "error_code": "INVALID_PATH",
                },
            )
        
        query = str(request.query_params) if request.query_params else ""
        valid, error_msg = self._validate_query(query)
        if not valid:
            logger.warning("Invalid query: %s - %s", query, error_msg)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": error_msg,
                    "error_code": "INVALID_QUERY",
                },
            )
        
        headers = dict(request.headers)
        valid, error_msg = self._validate_headers(headers)
        if not valid:
            logger.warning("Invalid headers: %s", error_msg)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": error_msg,
                    "error_code": "INVALID_HEADERS",
                },
            )
        
        return await call_next(request)

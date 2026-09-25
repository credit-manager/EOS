import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

SUPPORTED_VERSIONS = ["v1"]
DEFAULT_VERSION = "v1"
API_PREFIX = "/api/"


class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if not path.startswith(API_PREFIX):
            return await call_next(request)
        
        version_match = re.match(rf"{API_PREFIX}(v\d+)/", path)
        if not version_match:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "API version is required in the URL path",
                    "error_code": "INVALID_API_VERSION",
                    "supported_versions": SUPPORTED_VERSIONS,
                    "example": f"/api/v1{path[len(API_PREFIX):]}",
                },
            )
        
        version = version_match.group(1)
        if version not in SUPPORTED_VERSIONS:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"Unsupported API version: {version}",
                    "error_code": "UNSUPPORTED_API_VERSION",
                    "supported_versions": SUPPORTED_VERSIONS,
                    "current_version": DEFAULT_VERSION,
                },
            )
        
        request.state.api_version = version
        
        response = await call_next(request)
        
        response.headers["X-API-Version"] = version
        response.headers["X-API-Supported-Versions"] = ", ".join(SUPPORTED_VERSIONS)
        
        return response

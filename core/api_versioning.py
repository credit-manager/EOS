"""
P74.6 API Versioning Infrastructure
====================================
Supports:
  - URL prefix: /api/v1/..., /api/v2/...
  - Header: Accept-Version: v1
  - Default: v1
"""
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SUPPORTED_VERSIONS = {"v1": "1.0.0", "v2": "2.0.0"}
DEFAULT_VERSION = "v1"


def extract_version_from_path(path: str) -> tuple:
    match = re.match(r"^/api/(v\d+)/", path)
    if match:
        version = match.group(1)
        rest = path[match.end() - 1:]
        return version, rest
    return DEFAULT_VERSION, path


def extract_version_from_header(request: Request) -> str:
    accept = request.headers.get("Accept-Version", "")
    if accept:
        accept = accept.strip().lower()
        if accept.startswith("v"):
            return accept
        if accept in SUPPORTED_VERSIONS:
            return f"v{accept}"
    return DEFAULT_VERSION


class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/api/"):
            url_version, _ = extract_version_from_path(path)
            header_version = extract_version_from_header(request)

            if url_version != DEFAULT_VERSION and url_version not in SUPPORTED_VERSIONS:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "unsupported_version",
                        "message": f"API version '{url_version}' is not supported",
                        "supported_versions": list(SUPPORTED_VERSIONS.keys()),
                        "default_version": DEFAULT_VERSION,
                    }
                )

            effective_version = url_version if url_version != DEFAULT_VERSION else header_version
            request.state.api_version = effective_version
        else:
            request.state.api_version = DEFAULT_VERSION

        response = await call_next(request)
        response.headers["X-API-Version"] = request.state.api_version
        return response

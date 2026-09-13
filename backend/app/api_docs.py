from typing import Any

from pydantic import BaseModel, ConfigDict


class APIErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Validation error",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": "abc12345",
                    "details": {
                        "validation_errors": [
                            {"field": "body -> email", "message": "Invalid email format"}
                        ]
                    },
                }
            ]
        }
    )

    detail: str
    error_code: str
    request_id: str
    details: dict[str, Any] | None = None


class APIListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [],
                    "total": 0,
                    "limit": 20,
                    "offset": 0,
                }
            ]
        }
    )

    items: list
    total: int
    limit: int
    offset: int


class APISuccessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Operation completed successfully",
                    "data": {},
                }
            ]
        }
    )

    message: str
    data: dict[str, Any] | None = None


class APIDeleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Resource deleted successfully",
                }
            ]
        }
    )

    message: str


class APIPaginatedResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [],
                    "total": 100,
                    "limit": 20,
                    "offset": 0,
                    "has_more": True,
                }
            ]
        }
    )

    items: list
    total: int
    limit: int
    offset: int
    has_more: bool


class APIHealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "services": {
                        "database": "healthy",
                        "redis": "healthy",
                    },
                }
            ]
        }
    )

    status: str
    version: str
    services: dict[str, str]


class APIMetricsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "requests": {
                        "total": 1000,
                        "errors": 10,
                        "avg_duration_ms": 50.5,
                    },
                    "database": {
                        "queries": 500,
                        "slow_queries": 5,
                        "avg_duration_ms": 10.2,
                    },
                }
            ]
        }
    )

    requests: dict[str, Any]
    database: dict[str, Any]
    cache: dict[str, Any]


ERROR_RESPONSES = {
    400: {
        "model": APIErrorResponse,
        "description": "Bad request - Invalid input data",
    },
    401: {
        "model": APIErrorResponse,
        "description": "Unauthorized - Authentication required",
    },
    403: {
        "model": APIErrorResponse,
        "description": "Forbidden - Insufficient permissions",
    },
    404: {
        "model": APIErrorResponse,
        "description": "Not found - Resource does not exist",
    },
    409: {
        "model": APIErrorResponse,
        "description": "Conflict - Resource already exists",
    },
    422: {
        "model": APIErrorResponse,
        "description": "Validation error - Invalid request data",
    },
    429: {
        "model": APIErrorResponse,
        "description": "Rate limit exceeded - Too many requests",
    },
    500: {
        "model": APIErrorResponse,
        "description": "Internal server error - Unexpected error",
    },
    503: {
        "model": APIErrorResponse,
        "description": "Service unavailable - Service temporarily unavailable",
    },
}


def get_error_response(status_code: int) -> dict:
    return ERROR_RESPONSES.get(status_code, ERROR_RESPONSES[500])

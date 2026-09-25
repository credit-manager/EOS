import logging
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("2to-eos.errors")


class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    ORIGIN_NOT_ALLOWED = "ORIGIN_NOT_ALLOWED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_ACCEPTABLE = "NOT_ACCEPTABLE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    BAD_GATEWAY = "BAD_GATEWAY"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"


ERROR_STATUS_MAP = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.AUTHENTICATION_REQUIRED: 401,
    ErrorCode.AUTHORIZATION_DENIED: 403,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.RESOURCE_CONFLICT: 409,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.REQUEST_TIMEOUT: 504,
    ErrorCode.REQUEST_TOO_LARGE: 413,
    ErrorCode.ORIGIN_NOT_ALLOWED: 403,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.NOT_ACCEPTABLE: 406,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.UNPROCESSABLE_ENTITY: 422,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.BAD_GATEWAY: 502,
    ErrorCode.GATEWAY_TIMEOUT: 504,
}


ERROR_MESSAGES = {
    ErrorCode.VALIDATION_ERROR: "The request body or parameters failed validation",
    ErrorCode.AUTHENTICATION_REQUIRED: "Authentication is required to access this resource",
    ErrorCode.AUTHORIZATION_DENIED: "You do not have permission to perform this action",
    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found",
    ErrorCode.RESOURCE_CONFLICT: "The request conflicts with the current state of the resource",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests, please try again later",
    ErrorCode.REQUEST_TIMEOUT: "The request timed out",
    ErrorCode.REQUEST_TOO_LARGE: "The request body is too large",
    ErrorCode.ORIGIN_NOT_ALLOWED: "The request origin is not allowed",
    ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred",
    ErrorCode.SERVICE_UNAVAILABLE: "The service is temporarily unavailable",
    ErrorCode.METHOD_NOT_ALLOWED: "The HTTP method is not allowed for this endpoint",
    ErrorCode.NOT_ACCEPTABLE: "The requested media type is not acceptable",
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: "The request media type is not supported",
    ErrorCode.UNPROCESSABLE_ENTITY: "The request could not be processed",
    ErrorCode.TOO_MANY_REQUESTS: "Rate limit exceeded",
    ErrorCode.BAD_GATEWAY: "Bad gateway",
    ErrorCode.GATEWAY_TIMEOUT: "Gateway timeout",
}


def create_error_response(
    status_code: int,
    message: str,
    error_code: str,
    request_id: str,
    details: dict | None = None,
) -> JSONResponse:
    content = {
        "detail": message,
        "error_code": error_code,
        "request_id": request_id,
    }
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


def create_error_from_code(
    error_code: str,
    request_id: str,
    details: dict | None = None,
) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(error_code, 500)
    message = ERROR_MESSAGES.get(error_code, "An error occurred")
    return create_error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        request_id=request_id,
        details=details,
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", str(uuid4())[:8])
        try:
            response = await call_next(request)
            return response
        except StarletteHTTPException as exc:
            error_code = _get_error_code_from_status(exc.status_code)
            logger.warning(
                "[%s] HTTP %d: %s (code: %s)",
                request_id,
                exc.status_code,
                exc.detail,
                error_code,
            )
            return create_error_response(
                status_code=exc.status_code,
                message=str(exc.detail),
                error_code=error_code,
                request_id=request_id,
            )
        except RequestValidationError as exc:
            errors = []
            for error in exc.errors():
                loc = " -> ".join(str(loc) for loc in error.get("loc", []))
                msg = error.get("msg", "Validation error")
                errors.append({"field": loc, "message": msg})
            logger.warning(
                "[%s] Validation error: %s",
                request_id,
                errors,
            )
            return create_error_response(
                status_code=422,
                message="Validation error",
                error_code=ErrorCode.VALIDATION_ERROR,
                request_id=request_id,
                details={"validation_errors": errors},
            )
        except Exception as exc:
            logger.error(
                "[%s] Unhandled exception: %s\n%s",
                request_id,
                str(exc),
                traceback.format_exc(),
            )
            return create_error_response(
                status_code=500,
                message="Internal server error",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                request_id=request_id,
            )


def _get_error_code_from_status(status_code: int) -> str:
    status_to_code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_REQUIRED,
        403: ErrorCode.AUTHORIZATION_DENIED,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        406: ErrorCode.NOT_ACCEPTABLE,
        409: ErrorCode.RESOURCE_CONFLICT,
        413: ErrorCode.REQUEST_TOO_LARGE,
        415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        422: ErrorCode.UNPROCESSABLE_ENTITY,
        429: ErrorCode.TOO_MANY_REQUESTS,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        502: ErrorCode.BAD_GATEWAY,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.GATEWAY_TIMEOUT,
    }
    return status_to_code.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        error_code = _get_error_code_from_status(exc.status_code)
        logger.warning(
            "[%s] HTTP %d: %s (code: %s)",
            request_id,
            exc.status_code,
            exc.detail,
            error_code,
        )
        return create_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_code=error_code,
            request_id=request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg", "Validation error")
            errors.append({"field": loc, "message": msg})
        logger.warning(
            "[%s] Validation error: %s",
            request_id,
            errors,
        )
        return create_error_response(
            status_code=422,
            message="Validation error",
            error_code=ErrorCode.VALIDATION_ERROR,
            request_id=request_id,
            details={"validation_errors": errors},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "[%s] Unhandled exception: %s\n%s",
            request_id,
            str(exc),
            traceback.format_exc(),
        )
        return create_error_response(
            status_code=500,
            message="Internal server error",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id,
        )
